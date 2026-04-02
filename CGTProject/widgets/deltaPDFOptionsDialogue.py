# AP 2026

'''
 options widget to generate delta PDF from temperature dependent scattering data
#need scrollable options with previews and results along the way for:
--setup
- lattice params

--mask options
- option to choose either bragg mask or intensity mask
- bragg mask peak punch radius
- bragg mask coeffs
- bragg mask thresh
- intensity mask thresh
- intensity mask radius
- generate mask at coords

--setup kernal
- option to choose kernal (only gaussian for right now)
- options for that kernal (kernal dependant)

--set taper for window
- choose window type (set_ellipsoidal_tukey_window, set_tukey_window, set_hexagonal_tukey_window)
- set turkey alphas

--setup padding
- choose padding triple tuple

--submit to preform FFT

#TODO will need a way to reload self.dpdf when the user unclicks something they have already previewed

'''
#also allow logscale option for plottedGraphWidget

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QSpinBox, QDoubleSpinBox, QLabel, QPushButton, QComboBox, QFormLayout, QDialog, QScrollArea, QProgressBar
from PyQt5.QtCore import pyqtSignal, Qt, QObject, QThread, QTimer
import numpy as np
from typing import Optional

from nxs_analysis_tools.pairdistribution import DeltaPDF
from nxs_analysis_tools.pairdistribution import Gaussian3DKernel
from nxs_analysis_tools.datareduction import plot_slice
from nexusformat.nexus import NXdata, NeXusError, nxsetmemory, NXfield

from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget


class _DeltaPDFLoadWorker(QObject):
    finished = pyqtSignal(object)  # DeltaPDF
    failed = pyqtSignal(str)

    def __init__(self, nxdata: NXdata):
        super().__init__()
        self._nxdata = nxdata

    def run(self):
        try:
            dpdf = DeltaPDF()
            dpdf.set_data(self._nxdata)
            self.finished.emit(dpdf)
        except Exception as e:
            self.failed.emit(str(e))


class _DeltaPDFBuildWorker(QObject):
    finished = pyqtSignal(object)  # DeltaPDF
    failed = pyqtSignal(str)

    def __init__(self, nxdata: NXdata, options: dict):
        super().__init__()
        self._nxdata = nxdata
        self._options = options

    def _generate_mask(self, dpdf: DeltaPDF):
        opt = self._options
        mask = None

        if opt.get("bragg_mask", False):
            punch_radius = opt.get("bragg_punch_radius") if opt.get("bragg_punch_radius_enabled") else None
            if opt.get("bragg_coeffs_enabled"):
                coeffs = (
                    opt.get("bragg_coeffs_h"),
                    opt.get("bragg_coeffs_hk"),
                    opt.get("bragg_coeffs_k"),
                    opt.get("bragg_coeffs_kl"),
                    opt.get("bragg_coeffs_l"),
                    opt.get("bragg_coeffs_lh"),
                )
            else:
                coeffs = (None, None, None, None, None, None)
            thresh = opt.get("bragg_thresh") if opt.get("bragg_thresh_enabled") else None
            mask = dpdf.generate_bragg_mask(punch_radius=punch_radius, coeffs=coeffs, thresh=thresh)

        if opt.get("intensity_mask", False):
            thresh = opt.get("intensity_thresh") if opt.get("intensity_thresh_enabled") else None
            radius = opt.get("intensity_radius") if opt.get("intensity_radius_enabled") else None
            mask = dpdf.generate_intensity_mask(thresh=thresh, radius=radius)

        if opt.get("custom_mask", False):
            coords = (
                opt.get("custom_mask_x"),
                opt.get("custom_mask_y"),
                opt.get("custom_mask_z"),
            )
            mask = dpdf.generate_mask_at_coord(coords=coords)

        return mask

    def run(self):
        try:
            opt = self._options
            dpdf = DeltaPDF()
            dpdf.set_data(self._nxdata)

            dpdf.set_lattice_params((
                opt["a"], opt["b"], opt["c"],
                opt["alpha"], opt["beta"], opt["gamma"],
            ))

            mask = self._generate_mask(dpdf)
            if mask is not None:
                dpdf.add_mask(mask)
                dpdf.punch()

            kernel_kind = opt.get("kernel_kind")
            if kernel_kind == "Gaussian":
                size = opt.get("gaussian_size")
                dpdf.set_kernel(Gaussian3DKernel(stddev=opt.get("gaussian_stddev"), size=size))
                dpdf.interpolate()

            taper_kind = opt.get("taper_kind")
            if taper_kind == "Tukey":
                try:
                    dpdf.set_tukey_window(turkey_alphas=opt.get("tukey_alpha"))
                except TypeError:
                    dpdf.set_tukey_window()
            elif taper_kind == "Ellipsoidal":
                alpha = opt.get("ell_alpha")
                try:
                    dpdf.set_ellipsoidal_tukey_window(turkey_alphas=alpha)
                except TypeError:
                    try:
                        dpdf.set_ellipsoidal_tukey_window(turkey_alphas=(alpha[0], alpha[2], alpha[4]))
                    except Exception:
                        pass
            elif taper_kind == "Hexagonal":
                try:
                    dpdf.set_hexagonal_tukey_window(turkey_alphas=opt.get("hex_alpha"))
                except TypeError:
                    dpdf.set_hexagonal_tukey_window(turkey_alphas=opt.get("hex_alpha")[0])

            padding = opt.get("padding")
            if padding and tuple(padding) != (0, 0, 0):
                dpdf.pad(padding=tuple(padding))

            dpdf.perform_fft()
            self.finished.emit(dpdf)
        except Exception as e:
            self.failed.emit(str(e))


class DeltaPDFOptionsWidget(QDialog):
    generateDeltaPDF = pyqtSignal(dict)  # Signal to indicate Gaussian filter state and sigma value
    
    def __init__(self, nxdata:NXdata, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delta PDF Options")
        self.setModal(True)
        self.resize(800, 600)
        layout = QVBoxLayout()
        
        self.nxdata = nxdata
        # IMPORTANT: DeltaPDF.set_data(...) can be very expensive (may materialize the full 3D volume).
        # We load it in the background for previews, and compute the final dpdf in the background on OK.
        self._preview_dpdf: Optional[DeltaPDF] = None
        self._result_dpdf: Optional[DeltaPDF] = None

        self._preload_thread: Optional[QThread] = None
        self._preload_worker: Optional[_DeltaPDFLoadWorker] = None
        self._preload_in_progress: bool = False

        self._build_thread: Optional[QThread] = None
        self._build_worker: Optional[_DeltaPDFBuildWorker] = None
        self._build_in_progress: bool = False

        self._cancelled: bool = False
        
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        
        scrollContent = QWidget()
        self.formLayout = QFormLayout(scrollContent)
        scrollArea.setWidget(scrollContent)
        
        label = QLabel("Options for Generating Delta PDF:")
        label.setAlignment(Qt.AlignCenter)
        self.formLayout.addWidget(label)
        
        
        # # Gaussian Filter Options
        # self.generateDeltaPDFCheckBox = QCheckBox("Generate Delta PDF")
        # self.generateDeltaPDFCheckBox.stateChanged.connect(self.onGenerateDeltaPDFStateChanged)
        
        # self.optionsLabel = QLabel("Options: ")
        # self.optionsComboBox = QComboBox()
        # self.optionsComboBox.addItems(["Option 1", "Option 2", "Option 3"])
        
        self.initSetup()
        self.initMaskOptions()
        self.initKernal()
        self.initTaper()
        self.initPadding()
        

        # self.formLayout.addWidget(self.optionsLabel)
        # self.formLayout.addWidget(self.optionsComboBox)
        
        # self.formLayout.addWidget(self.generateDeltaPDFCheckBox)
        # self.formLayout.addLayout(optionsLayout)
        
        layout.addWidget(scrollArea)

        # Simple busy indicator + status text.
        self.statusLabel = QLabel("")
        layout.addWidget(self.statusLabel)
        self.busyBar = QProgressBar()
        self.busyBar.setRange(0, 1)
        self.busyBar.setVisible(False)
        layout.addWidget(self.busyBar)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self._onOkClicked)
        layout.addWidget(self.ok_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._onCancelClicked)
        layout.addWidget(self.cancel_button)
        
        
        self.setLayout(layout)

        # Kick off preview data load after the dialog has a chance to show.
        QTimer.singleShot(0, self._startPreviewPreload)

    def _setBusy(self, busy: bool, message: str = "", *, disable_ok: bool = True):
        self.busyBar.setVisible(busy)
        self.busyBar.setRange(0, 0 if busy else 1)
        self.statusLabel.setText(message)
        if disable_ok:
            self.ok_button.setEnabled(not busy)

    def _startPreviewPreload(self):
        if self._preview_dpdf is not None or self._preload_in_progress:
            return
        self._preload_in_progress = True
        self._setBusy(True, "Loading data for previews…", disable_ok=False)

        thread = QThread(self)
        worker = _DeltaPDFLoadWorker(self.nxdata)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._onPreviewPreloadFinished)
        worker.failed.connect(self._onPreviewPreloadFailed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        self._preload_thread = thread
        self._preload_worker = worker
        thread.start()

    def _onPreviewPreloadFinished(self, dpdf: DeltaPDF):
        self._preview_dpdf = dpdf
        self._preload_in_progress = False
        if not self._build_in_progress:
            self._setBusy(False, "", disable_ok=False)

    def _onPreviewPreloadFailed(self, msg: str):
        self._preload_in_progress = False
        if not self._build_in_progress:
            self._setBusy(False, f"Preview load failed: {msg}", disable_ok=False)

    def _collect_options(self) -> dict:
        return {
            "a": float(self.aSpinBox.value()),
            "b": float(self.bSpinBox.value()),
            "c": float(self.cSpinBox.value()),
            "alpha": float(self.alphaSpinBox.value()),
            "beta": float(self.betaSpinBox.value()),
            "gamma": float(self.gammaSpinBox.value()),

            "bragg_mask": bool(self.braggMaskCheckBox.isChecked()),
            "bragg_punch_radius_enabled": bool(self.braggPunchRadiusCheckBox.isChecked()),
            "bragg_punch_radius": float(self.braggPunchRadius.value()),
            "bragg_coeffs_enabled": bool(self.braggCoeffsCheckBox.isChecked()),
            "bragg_coeffs_h": float(self.braggCoeffsH.value()),
            "bragg_coeffs_hk": float(self.braggCoeffsHK.value()),
            "bragg_coeffs_k": float(self.braggCoeffsK.value()),
            "bragg_coeffs_kl": float(self.braggCoeffsKL.value()),
            "bragg_coeffs_l": float(self.braggCoeffsL.value()),
            "bragg_coeffs_lh": float(self.braggCoeffsLH.value()),
            "bragg_thresh_enabled": bool(self.braggThreshCheckBox.isChecked()),
            "bragg_thresh": float(self.braggThresh.value()),

            "intensity_mask": bool(self.intensityMaskCheckBox.isChecked()),
            "intensity_thresh_enabled": bool(self.intensityThreshCheckBox.isChecked()),
            "intensity_thresh": float(self.intensityThresh.value()),
            "intensity_radius_enabled": bool(self.intensityRadiusCheckBox.isChecked()),
            "intensity_radius": float(self.intensityRadius.value()),

            "custom_mask": bool(self.customMaskCheckBox.isChecked()),
            "custom_mask_x": float(self.customMaskXSpin.value()),
            "custom_mask_y": float(self.customMaskYSpin.value()),
            "custom_mask_z": float(self.customMaskZSpin.value()),

            "kernel_kind": str(self.kernalComboBox.currentText()),
            "gaussian_stddev": float(self.gaussianStdev.value()),
            "gaussian_size": (
                int(self.gaussianSizeX.value()),
                int(self.gaussianSizeY.value()),
                int(self.gaussianSizeZ.value()),
            ),

            "taper_kind": str(self.taperComboBox.currentText()),
            "tukey_alpha": (
                float(self.tukeyAlphaH.value()),
                float(self.tukeyAlphaK.value()),
                float(self.tukeyAlphaL.value()),
            ),
            "ell_alpha": (
                float(self.ellAlphaH.value()),
                float(self.ellAlphaHK.value()),
                float(self.ellAlphaK.value()),
                float(self.ellAlphaKL.value()),
                float(self.ellAlphaL.value()),
                float(self.ellAlphaLH.value()),
            ),
            "hex_alpha": (
                float(self.hexAlphaH.value()),
                float(self.hexAlphaK.value()),
                float(self.hexAlphaHK.value()),
                float(self.hexAlphaL.value()),
            ),

            "padding": (
                int(self.paddingX.value()),
                int(self.paddingY.value()),
                int(self.paddingZ.value()),
            ),
        }

    def _onOkClicked(self):
        if self._build_in_progress:
            return
        self._build_in_progress = True
        self._setBusy(True, "Computing DeltaPDF (FFT)…")
        options = self._collect_options()

        thread = QThread(self)
        worker = _DeltaPDFBuildWorker(self.nxdata, options)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._onBuildFinished)
        worker.failed.connect(self._onBuildFailed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        self._build_thread = thread
        self._build_worker = worker
        thread.start()

    def _onBuildFinished(self, dpdf: DeltaPDF):
        self._result_dpdf = dpdf
        self._build_in_progress = False
        self._setBusy(False, "")
        if not self._cancelled:
            self.accept()

    def _onBuildFailed(self, msg: str):
        self._build_in_progress = False
        self._setBusy(False, f"DeltaPDF failed: {msg}")

    def _onCancelClicked(self):
        self._cancelled = True
        self.reject()

    def _get_preview_dpdf(self) -> Optional[DeltaPDF]:
        """Returns the preview DeltaPDF if loaded; otherwise triggers background load."""
        if self._preview_dpdf is not None:
            return self._preview_dpdf
        self._startPreviewPreload()
        return None
        
        
    def initSetup(self):
        # setup for lattice parameters: a,b,c (angstrom), alpha, beta, gamma (degrees)
        hlayout = QHBoxLayout()
        self.aSpinBox = QDoubleSpinBox()
        self.aSpinBox.setRange(0.1, 1000.0)
        self.aSpinBox.setValue(1.0)
        self.aSpinBox.setSuffix(" Å")
        hlayout.addWidget(QLabel("a:"))
        hlayout.addWidget(self.aSpinBox)
        
        self.bSpinBox = QDoubleSpinBox()
        self.bSpinBox.setRange(0.1, 1000.0)
        self.bSpinBox.setValue(1.0)
        self.bSpinBox.setSuffix(" Å")
        hlayout.addWidget(QLabel("b:"))
        hlayout.addWidget(self.bSpinBox)
        
        self.cSpinBox = QDoubleSpinBox()
        self.cSpinBox.setRange(0.1, 1000.0)
        self.cSpinBox.setValue(1.0)
        self.cSpinBox.setSuffix(" Å")
        hlayout.addWidget(QLabel("c:"))
        hlayout.addWidget(self.cSpinBox)
        
        self.alphaSpinBox = QDoubleSpinBox()
        self.alphaSpinBox.setRange(0.1, 180.0)
        self.alphaSpinBox.setValue(90.0)
        self.alphaSpinBox.setSuffix(" °")
        hlayout.addWidget(QLabel("α:"))
        hlayout.addWidget(self.alphaSpinBox)
        
        self.betaSpinBox = QDoubleSpinBox()
        self.betaSpinBox.setRange(0.1, 180.0)
        self.betaSpinBox.setValue(90.0)
        self.betaSpinBox.setSuffix(" °")
        hlayout.addWidget(QLabel("β:"))
        hlayout.addWidget(self.betaSpinBox)
        
        self.gammaSpinBox = QDoubleSpinBox()
        self.gammaSpinBox.setRange(0.1, 180.0)
        self.gammaSpinBox.setValue(90.0)
        self.gammaSpinBox.setSuffix(" °")
        hlayout.addWidget(QLabel("γ:"))
        hlayout.addWidget(self.gammaSpinBox)
        
        self.formLayout.addRow(QLabel("Lattice Parameters:"), hlayout)
        
    def getDeltaPDF(self):
        # If OK was used, the result is computed in the background and stored here.
        # (Fallback to synchronous build only if someone calls getDeltaPDF directly.)
        if self._result_dpdf is not None:
            return self._result_dpdf

        # Synchronous fallback (kept for compatibility).
        worker = _DeltaPDFBuildWorker(self.nxdata, self._collect_options())
        result_container = {"dpdf": None, "err": None}

        def _done(d):
            result_container["dpdf"] = d

        def _fail(m):
            result_container["err"] = m

        worker.finished.connect(_done)
        worker.failed.connect(_fail)
        worker.run()
        if result_container["err"]:
            raise RuntimeError(result_container["err"])
        return result_container["dpdf"]
    
    def generateMask(self, dpdf):
        mask = None
        if self.braggMaskCheckBox.isChecked():
            if self.braggPunchRadiusCheckBox.isChecked():
                punch_radius = self.braggPunchRadius.value()
            else:                
                punch_radius = None
            if self.braggCoeffsCheckBox.isChecked():
                coeffs = (
                    self.braggCoeffsH.value(),
                    self.braggCoeffsHK.value(),
                    self.braggCoeffsK.value(),
                    self.braggCoeffsKL.value(),
                    self.braggCoeffsL.value(),
                    self.braggCoeffsLH.value(),
                )
            else:
                coeffs = (None, None, None, None, None, None)
            if self.braggThreshCheckBox.isChecked():
                thresh = self.braggThresh.value()
            else:                
                thresh = None
            print(punch_radius, coeffs, thresh)
            mask = dpdf.generate_bragg_mask(punch_radius=punch_radius, coeffs=coeffs, thresh=thresh)
        if self.intensityMaskCheckBox.isChecked():
            if self.intensityThreshCheckBox.isChecked():
                thresh = self.intensityThresh.value()
            else:
                thresh = None
            if self.intensityRadiusCheckBox.isChecked():
                radius = self.intensityRadius.value()
            else:
                radius = None
            mask = dpdf.generate_intensity_mask(thresh=thresh, radius=radius)
        if self.customMaskCheckBox.isChecked():
            coords = (self.customMaskXSpin.value(), self.customMaskYSpin.value(), self.customMaskZSpin.value())
            mask = dpdf.generate_mask_at_coord(coords=coords)
            
        return mask
        
        
        
    def initMaskOptions(self):
        # --mask options
        # - option to choose either bragg mask or intensity mask
        # - bragg mask peak punch radius
        # - bragg mask coeffs
        # - bragg mask thresh
        # - intensity mask thresh
        # - intensity mask radius
        # - generate mask at coords
        # Placeholder for mask options
        masklayout = QVBoxLayout()
        masklayout.addWidget(QLabel("Mask Options:"))

        # Bragg Mask
        self.braggMaskCheckBox = QCheckBox("Bragg Mask")
        masklayout.addWidget(self.braggMaskCheckBox)

        self.braggMaskOptions = QWidget()
        braggLayout = QFormLayout(self.braggMaskOptions)
        braggLayout.setContentsMargins(20, 0, 0, 0)

        self.braggPunchRadiusCheckBox = QCheckBox("Peak Punch Radius")
        braggLayout.addRow(self.braggPunchRadiusCheckBox)
        self.braggPunchRadius = QDoubleSpinBox()
        self.braggPunchRadius.setRange(0.0, 100.0)
        self.braggPunchRadius.setValue(0.5)
        self.braggPunchRadius.hide()
        braggLayout.addRow(self.braggPunchRadius)
        self.braggPunchRadiusCheckBox.stateChanged.connect(
            lambda state: self.braggPunchRadius.setVisible(state == Qt.Checked))

        self.braggCoeffsCheckBox = QCheckBox("Coeffs")
        braggLayout.addRow(self.braggCoeffsCheckBox)
        # bragg coeffs as 6-tuple: (H, HK, K, KL, L, LH)
        self.braggCoeffsHLabel = QLabel("Coeff H:")
        self.braggCoeffsH = QDoubleSpinBox()
        self.braggCoeffsH.setRange(0.0, 100.0)
        self.braggCoeffsH.setValue(1.0)
        self.braggCoeffsHLabel.hide()
        self.braggCoeffsH.hide()
        braggLayout.addRow(self.braggCoeffsHLabel, self.braggCoeffsH)

        self.braggCoeffsHKLabel = QLabel("Coeff HK:")
        self.braggCoeffsHK = QDoubleSpinBox()
        self.braggCoeffsHK.setRange(0.0, 100.0)
        self.braggCoeffsHK.setValue(1.0)
        self.braggCoeffsHKLabel.hide()
        self.braggCoeffsHK.hide()
        braggLayout.addRow(self.braggCoeffsHKLabel, self.braggCoeffsHK)

        self.braggCoeffsKLabel = QLabel("Coeff K:")
        self.braggCoeffsK = QDoubleSpinBox()
        self.braggCoeffsK.setRange(0.0, 100.0)
        self.braggCoeffsK.setValue(1.0)
        self.braggCoeffsKLabel.hide()
        self.braggCoeffsK.hide()
        braggLayout.addRow(self.braggCoeffsKLabel, self.braggCoeffsK)

        self.braggCoeffsKLLabel = QLabel("Coeff KL:")
        self.braggCoeffsKL = QDoubleSpinBox()
        self.braggCoeffsKL.setRange(0.0, 100.0)
        self.braggCoeffsKL.setValue(1.0)
        self.braggCoeffsKLLabel.hide()
        self.braggCoeffsKL.hide()
        braggLayout.addRow(self.braggCoeffsKLLabel, self.braggCoeffsKL)

        self.braggCoeffsLLabel = QLabel("Coeff L:")
        self.braggCoeffsL = QDoubleSpinBox()
        self.braggCoeffsL.setRange(0.0, 100.0)
        self.braggCoeffsL.setValue(1.0)
        self.braggCoeffsLLabel.hide()
        self.braggCoeffsL.hide()
        braggLayout.addRow(self.braggCoeffsLLabel, self.braggCoeffsL)

        self.braggCoeffsLHLabel = QLabel("Coeff LH:")
        self.braggCoeffsLH = QDoubleSpinBox()
        self.braggCoeffsLH.setRange(0.0, 100.0)
        self.braggCoeffsLH.setValue(1.0)
        self.braggCoeffsLHLabel.hide()
        self.braggCoeffsLH.hide()
        braggLayout.addRow(self.braggCoeffsLHLabel, self.braggCoeffsLH)

        self.braggCoeffsCheckBox.stateChanged.connect(self._onBraggCoeffsToggled)

        self.braggThreshCheckBox = QCheckBox("Threshold")
        braggLayout.addRow(self.braggThreshCheckBox)
        self.braggThresh = QDoubleSpinBox()
        self.braggThresh.setRange(0.0, 1000.0)
        self.braggThresh.setValue(1.0)
        self.braggThresh.hide()
        braggLayout.addRow(self.braggThresh)
        self.braggThreshCheckBox.stateChanged.connect(
            lambda state: self.braggThresh.setVisible(state == Qt.Checked))
        self.braggMaskOptions.hide()
        masklayout.addWidget(self.braggMaskOptions)

        self.braggMaskCheckBox.stateChanged.connect(
            lambda state: self.braggMaskOptions.setVisible(state == Qt.Checked))

        # Intensity Mask
        self.intensityMaskCheckBox = QCheckBox("Intensity Mask")
        masklayout.addWidget(self.intensityMaskCheckBox)

        self.intensityMaskOptions = QWidget()
        intensityLayout = QFormLayout(self.intensityMaskOptions)
        intensityLayout.setContentsMargins(20, 0, 0, 0)

        # Threshold option: checkbox + spinbox shown when checked
        self.intensityThreshCheckBox = QCheckBox("Threshold")
        intensityLayout.addRow(self.intensityThreshCheckBox)
        self.intensityThresh = QDoubleSpinBox()
        self.intensityThresh.setRange(0.0, 1000.0)
        self.intensityThresh.setValue(1.0)
        self.intensityThresh.hide()
        intensityLayout.addRow(self.intensityThresh)
        self.intensityThreshCheckBox.stateChanged.connect(
            lambda state: self.intensityThresh.setVisible(state == Qt.Checked))

        # Radius option: checkbox + spinbox shown when checked
        self.intensityRadiusCheckBox = QCheckBox("Radius")
        intensityLayout.addRow(self.intensityRadiusCheckBox)
        self.intensityRadius = QDoubleSpinBox()
        self.intensityRadius.setRange(0.0, 100.0)
        self.intensityRadius.setValue(0.5)
        self.intensityRadius.hide()
        intensityLayout.addRow(self.intensityRadius)
        self.intensityRadiusCheckBox.stateChanged.connect(
            lambda state: self.intensityRadius.setVisible(state == Qt.Checked))

        self.intensityMaskOptions.hide()
        masklayout.addWidget(self.intensityMaskOptions)

        self.intensityMaskCheckBox.stateChanged.connect(
            lambda state: self.intensityMaskOptions.setVisible(state == Qt.Checked))

        # Custom Mask
        self.customMaskCheckBox = QCheckBox("Custom Mask")
        masklayout.addWidget(self.customMaskCheckBox)

        self.customMaskOptions = QWidget()
        customLayout = QFormLayout(self.customMaskOptions)
        customLayout.setContentsMargins(20, 0, 0, 0)

        # Inline inputs to pick a 3-tuple coordinate
        self.customMaskXSpin = QDoubleSpinBox()
        self.customMaskXSpin.setRange(-1e6, 1e6)
        self.customMaskXSpin.setDecimals(6)
        self.customMaskXSpin.setValue(0.0)
        customLayout.addRow(QLabel("X:"), self.customMaskXSpin)

        self.customMaskYSpin = QDoubleSpinBox()
        self.customMaskYSpin.setRange(-1e6, 1e6)
        self.customMaskYSpin.setDecimals(6)
        self.customMaskYSpin.setValue(0.0)
        customLayout.addRow(QLabel("Y:"), self.customMaskYSpin)

        self.customMaskZSpin = QDoubleSpinBox()
        self.customMaskZSpin.setRange(-1e6, 1e6)
        self.customMaskZSpin.setDecimals(6)
        self.customMaskZSpin.setValue(0.0)
        customLayout.addRow(QLabel("Z:"), self.customMaskZSpin)

        self.customMaskOptions.hide()
        masklayout.addWidget(self.customMaskOptions)

        self.customMaskCheckBox.stateChanged.connect(
            lambda state: self.customMaskOptions.setVisible(state == Qt.Checked))

        self.formLayout.addRow(masklayout)
        seeMaskPreviewButton = QPushButton("See Mask Preview")
        seeMaskPreviewButton.clicked.connect(lambda: self.generate_mask_preview())
        self.formLayout.addRow(seeMaskPreviewButton)
        
        self.maskPlotPreview = PlottedGraphWidget()
        self.maskPlotPreview.setVisible(False)
        self.formLayout.addRow(self.maskPlotPreview)
    def _show_empty_preview(self, widget: PlottedGraphWidget, title: str):
        widget.ax_main.clear()
        widget.ax_main.set_title(title)
        widget.canvas_main.draw()


    def _onBraggCoeffsToggled(self, state: int):
        visible = state == Qt.Checked
        for label, spinbox in (
            (self.braggCoeffsHLabel, self.braggCoeffsH),
            (self.braggCoeffsHKLabel, self.braggCoeffsHK),
            (self.braggCoeffsKLabel, self.braggCoeffsK),
            (self.braggCoeffsKLLabel, self.braggCoeffsKL),
            (self.braggCoeffsLLabel, self.braggCoeffsL),
            (self.braggCoeffsLHLabel, self.braggCoeffsLH),
        ):
            label.setVisible(visible)
            spinbox.setVisible(visible)
        
            
    def generate_mask_preview(self):
        # plt.pcolormesh([:,:,mask.shape[2]//2].transpose())
        # plt.gca().set_aspect(dpdf.lattice_params[1]/dpdf.lattice_params[0])
        # ensure lattice params are set on the preview dpdf
        dpdf = self._get_preview_dpdf()
        if dpdf is None:
            self._setBusy(True, "Loading data for previews…", disable_ok=False)
            return
        try:
            dpdf.set_lattice_params((
                self.aSpinBox.value(), self.bSpinBox.value(), self.cSpinBox.value(),
                self.alphaSpinBox.value(), self.betaSpinBox.value(), self.gammaSpinBox.value()
            ))
        except Exception:
            pass
        self.maskPlotPreview.setVisible(True)
        mask = self.generateMask(dpdf)
        if mask is not None:
            self.maskPlotPreview.updatePColorMeshPlot(mask[:,:,mask.shape[2]//2].transpose())
            self.maskPlotPreview.ax_main.set_aspect(dpdf.lattice_params[1]/dpdf.lattice_params[0])
        else:
            self._show_empty_preview(self.maskPlotPreview, "Mask Preview (no mask generated)")

    def initKernal(self):
        kernalLayout = QVBoxLayout()
        kernalLayout.addWidget(QLabel("Fill in Missing Data (Kernal Options):"))

        self.kernalComboBox = QComboBox()
        self.kernalComboBox.addItems(["Select Kernal", "Gaussian", "Other Kernal"])
        kernalLayout.addWidget(self.kernalComboBox)

        # Gaussian options
        self.gaussianOptions = QWidget()
        gaussLayout = QFormLayout(self.gaussianOptions)
        gaussLayout.setContentsMargins(20, 0, 0, 0)
        self.gaussianStdev = QDoubleSpinBox()
        self.gaussianStdev.setRange(0.01, 100.0)
        self.gaussianStdev.setValue(1.0)
        gaussLayout.addRow(QLabel("Stdev:"), self.gaussianStdev)
        # Gaussian kernel size (integers)
        self.gaussianSizeX = QSpinBox()
        self.gaussianSizeX.setRange(1, 201)
        self.gaussianSizeX.setValue(10)
        gaussLayout.addRow(QLabel("Size X:"), self.gaussianSizeX)

        self.gaussianSizeY = QSpinBox()
        self.gaussianSizeY.setRange(1, 201)
        self.gaussianSizeY.setValue(10)
        gaussLayout.addRow(QLabel("Size Y:"), self.gaussianSizeY)

        self.gaussianSizeZ = QSpinBox()
        self.gaussianSizeZ.setRange(1, 201)
        self.gaussianSizeZ.setValue(10)
        gaussLayout.addRow(QLabel("Size Z:"), self.gaussianSizeZ)

        kernalLayout.addWidget(self.gaussianOptions)

        # Other Kernal options (placeholder)
        self.otherKernalOptions = QWidget()
        otherLayout = QFormLayout(self.otherKernalOptions)
        otherLayout.setContentsMargins(20, 0, 0, 0)
        otherLayout.addRow(QLabel("No options available yet."))
        self.otherKernalOptions.hide()
        kernalLayout.addWidget(self.otherKernalOptions)

        self.kernalComboBox.currentTextChanged.connect(self._onKernalChanged)

        self.formLayout.addRow(kernalLayout)
        seeKernalPreviewButton = QPushButton("See Kernal Preview")
        self.formLayout.addRow(seeKernalPreviewButton)
        seeKernalPreviewButton.clicked.connect(lambda: self.generate_kernal_preview())
        
        self.kernalPlotPreview = PlottedGraphWidget()
        self.kernalPlotPreview.setVisible(False)
        self.formLayout.addRow(self.kernalPlotPreview)

    def _onKernalChanged(self, text):
        self.gaussianOptions.setVisible(text == "Gaussian")
        self.otherKernalOptions.setVisible(text == "Other Kernal")
        
    def generate_kernal_preview(self):
        dpdf = self._get_preview_dpdf()
        if dpdf is None:
            self._setBusy(True, "Loading data for previews…", disable_ok=False)
            return
        self.kernalPlotPreview.setVisible(True)
        if self.kernalComboBox.currentText() == "Gaussian":
            # Generate a Gaussian kernel based on the sigma value
            size = (int(self.gaussianSizeX.value()), int(self.gaussianSizeY.value()), int(self.gaussianSizeZ.value()))
            dpdf.set_kernel(Gaussian3DKernel(stddev=self.gaussianStdev.value(), size=size))
            dpdf.interpolate()
            try:
                quadmesh = plot_slice(dpdf.interpolated[:,:,0.0])
                self.kernalPlotPreview.updateQuadMeshPlot(quadmesh)
            except Exception:
                self._show_empty_preview(self.kernalPlotPreview, "Kernel Preview (unable to render)")
        else:
            self._show_empty_preview(self.kernalPlotPreview, "Kernel Preview (select a kernel)")
        
        
    def initTaper(self):
        taperLayout = QVBoxLayout()
        taperLayout.addWidget(QLabel("Taper Options:"))

        self.taperComboBox = QComboBox()
        self.taperComboBox.addItems(["Ellipsoidal", "Tukey", "Hexagonal"])
        taperLayout.addWidget(self.taperComboBox)

        # Ellipsoidal options
        self.ellipsoidalOptions = QWidget()
        ellLayout = QFormLayout(self.ellipsoidalOptions)
        ellLayout.setContentsMargins(20, 0, 0, 0)
        # Ellipsoidal alphas as 6-tuple: (H, HK, K, KL, L, LH)
        self.ellAlphaH = QDoubleSpinBox()
        self.ellAlphaH.setRange(0.0, 1.0)
        self.ellAlphaH.setValue(0.5)
        self.ellAlphaH.setSingleStep(0.05)
        ellLayout.addRow(QLabel("Alpha H:"), self.ellAlphaH)

        self.ellAlphaHK = QDoubleSpinBox()
        self.ellAlphaHK.setRange(0.0, 1.0)
        self.ellAlphaHK.setValue(0.5)
        self.ellAlphaHK.setSingleStep(0.05)
        ellLayout.addRow(QLabel("Alpha HK:"), self.ellAlphaHK)

        self.ellAlphaK = QDoubleSpinBox()
        self.ellAlphaK.setRange(0.0, 1.0)
        self.ellAlphaK.setValue(0.5)
        self.ellAlphaK.setSingleStep(0.05)
        ellLayout.addRow(QLabel("Alpha K:"), self.ellAlphaK)

        self.ellAlphaKL = QDoubleSpinBox()
        self.ellAlphaKL.setRange(0.0, 1.0)
        self.ellAlphaKL.setValue(0.5)
        self.ellAlphaKL.setSingleStep(0.05)
        ellLayout.addRow(QLabel("Alpha KL:"), self.ellAlphaKL)

        self.ellAlphaL = QDoubleSpinBox()
        self.ellAlphaL.setRange(0.0, 1.0)
        self.ellAlphaL.setValue(0.5)
        self.ellAlphaL.setSingleStep(0.05)
        ellLayout.addRow(QLabel("Alpha L:"), self.ellAlphaL)

        self.ellAlphaLH = QDoubleSpinBox()
        self.ellAlphaLH.setRange(0.0, 1.0)
        self.ellAlphaLH.setValue(0.5)
        self.ellAlphaLH.setSingleStep(0.05)
        ellLayout.addRow(QLabel("Alpha LH:"), self.ellAlphaLH)

        taperLayout.addWidget(self.ellipsoidalOptions)

        # Tukey options (alpha as triple H,K,L)
        self.tukeyOptions = QWidget()
        tukLayout = QFormLayout(self.tukeyOptions)
        tukLayout.setContentsMargins(20, 0, 0, 0)
        self.tukeyAlphaH = QDoubleSpinBox()
        self.tukeyAlphaH.setRange(0.0, 1.0)
        self.tukeyAlphaH.setValue(0.5)
        self.tukeyAlphaH.setSingleStep(0.05)
        tukLayout.addRow(QLabel("Alpha H:"), self.tukeyAlphaH)
        self.tukeyAlphaK = QDoubleSpinBox()
        self.tukeyAlphaK.setRange(0.0, 1.0)
        self.tukeyAlphaK.setValue(0.5)
        self.tukeyAlphaK.setSingleStep(0.05)
        tukLayout.addRow(QLabel("Alpha K:"), self.tukeyAlphaK)
        self.tukeyAlphaL = QDoubleSpinBox()
        self.tukeyAlphaL.setRange(0.0, 1.0)
        self.tukeyAlphaL.setValue(0.5)
        self.tukeyAlphaL.setSingleStep(0.05)
        tukLayout.addRow(QLabel("Alpha L:"), self.tukeyAlphaL)
        self.tukeyOptions.hide()
        taperLayout.addWidget(self.tukeyOptions)

        # Hexagonal options (H, K, HK, L)
        self.hexagonalOptions = QWidget()
        hexLayout = QFormLayout(self.hexagonalOptions)
        hexLayout.setContentsMargins(20, 0, 0, 0)
        self.hexAlphaH = QDoubleSpinBox()
        self.hexAlphaH.setRange(0.0, 1.0)
        self.hexAlphaH.setValue(0.5)
        self.hexAlphaH.setSingleStep(0.05)
        hexLayout.addRow(QLabel("Alpha H:"), self.hexAlphaH)
        self.hexAlphaK = QDoubleSpinBox()
        self.hexAlphaK.setRange(0.0, 1.0)
        self.hexAlphaK.setValue(0.5)
        self.hexAlphaK.setSingleStep(0.05)
        hexLayout.addRow(QLabel("Alpha K:"), self.hexAlphaK)
        self.hexAlphaHK = QDoubleSpinBox()
        self.hexAlphaHK.setRange(0.0, 1.0)
        self.hexAlphaHK.setValue(0.5)
        self.hexAlphaHK.setSingleStep(0.05)
        hexLayout.addRow(QLabel("Alpha HK:"), self.hexAlphaHK)
        self.hexAlphaL = QDoubleSpinBox()
        self.hexAlphaL.setRange(0.0, 1.0)
        self.hexAlphaL.setValue(0.5)
        self.hexAlphaL.setSingleStep(0.05)
        hexLayout.addRow(QLabel("Alpha L:"), self.hexAlphaL)
        self.hexagonalOptions.hide()
        taperLayout.addWidget(self.hexagonalOptions)

        self.taperComboBox.currentTextChanged.connect(self._onTaperChanged)

        self.formLayout.addRow(taperLayout)
        seeTaperPreviewButton = QPushButton("See Taper Preview")
        self.formLayout.addRow(seeTaperPreviewButton)
        seeTaperPreviewButton.clicked.connect(lambda: self.generate_taper_preview())
        
        self.taperPlotPreview = PlottedGraphWidget()
        self.taperPlotPreview.setVisible(False)
        self.formLayout.addRow(self.taperPlotPreview)

    def _onTaperChanged(self, text):
        self.ellipsoidalOptions.setVisible(text == "Ellipsoidal")
        self.tukeyOptions.setVisible(text == "Tukey")
        self.hexagonalOptions.setVisible(text == "Hexagonal")
        
    def generate_taper_preview(self):
        dpdf = self._get_preview_dpdf()
        if dpdf is None:
            self._setBusy(True, "Loading data for previews…", disable_ok=False)
            return
        txt = self.taperComboBox.currentText()
        if txt == "Tukey":
            alpha = (self.tukeyAlphaH.value(), self.tukeyAlphaK.value(), self.tukeyAlphaL.value())
            try:
                dpdf.set_tukey_window(turkey_alphas=alpha)
            except TypeError:
                dpdf.set_tukey_window()
        elif txt == "Ellipsoidal":
            alpha = (
                self.ellAlphaH.value(),
                self.ellAlphaHK.value(),
                self.ellAlphaK.value(),
                self.ellAlphaKL.value(),
                self.ellAlphaL.value(),
                self.ellAlphaLH.value(),
            )
            try:
                # prefer a single alpha tuple if supported
                dpdf.set_ellipsoidal_tukey_window(turkey_alphas=alpha)
            except TypeError:
                # fallback to older 3-arg signature (H,K,L)
                try:
                    dpdf.set_ellipsoidal_tukey_window(turkey_alphas=(alpha[0], alpha[2], alpha[4]))
                except Exception:
                    pass
        elif txt == "Hexagonal":
            try:
                dpdf.set_hexagonal_tukey_window(turkey_alphas=(self.hexAlphaH.value(), self.hexAlphaK.value(), self.hexAlphaHK.value(), self.hexAlphaL.value()))
            except TypeError:
                dpdf.set_hexagonal_tukey_window(turkey_alphas=self.hexAlphaH.value())
        self.taperPlotPreview.setVisible(True)
        if getattr(dpdf, 'window', None) is not None:
            try:
                window = dpdf.window
                self.taperPlotPreview.updatePColorMeshPlot(window[:,:,window.shape[2]//2].transpose(), title="Taper Window")
            except Exception:
                self._show_empty_preview(self.taperPlotPreview, "Taper Preview (unable to render)")
        else:
            self._show_empty_preview(self.taperPlotPreview, "Taper Preview (no window generated)")

    def initPadding(self):
        # --setup padding
        # - choose padding triple tuple
        self.formLayout.addRow(QLabel("Padding Options:"))
        # padding as triple (X, Y, Z)
        padLayout = QHBoxLayout()
        self.paddingX = QSpinBox()
        self.paddingX.setRange(0, 500)
        self.paddingX.setValue(0)
        padLayout.addWidget(QLabel("X:"))
        padLayout.addWidget(self.paddingX)
        self.paddingY = QSpinBox()
        self.paddingY.setRange(0, 500)
        self.paddingY.setValue(0)
        padLayout.addWidget(QLabel("Y:"))
        padLayout.addWidget(self.paddingY)
        self.paddingZ = QSpinBox()
        self.paddingZ.setRange(0, 500)
        self.paddingZ.setValue(0)
        padLayout.addWidget(QLabel("Z:"))
        padLayout.addWidget(self.paddingZ)
        self.formLayout.addRow(padLayout)
        seePaddingPreviewButton = QPushButton("See Padding Preview")
        self.formLayout.addRow(seePaddingPreviewButton)
        seePaddingPreviewButton.clicked.connect(lambda: self.generate_padding_preview())

        self.paddingPlotPreview = PlottedGraphWidget()
        self.paddingPlotPreview.setVisible(False)
        self.formLayout.addRow(self.paddingPlotPreview)
        
    def generate_padding_preview(self):
        dpdf = self._get_preview_dpdf()
        if dpdf is None:
            self._setBusy(True, "Loading data for previews…", disable_ok=False)
            return
        padding = (int(self.paddingX.value()), int(self.paddingY.value()), int(self.paddingZ.value()))
        # store or use padding tuple as needed; preview placeholder
        if padding != (0, 0, 0):
            self.paddingTriple = padding
            dpdf.pad(padding=padding)
            self.paddingPlotPreview.setVisible(True)
            if getattr(dpdf, 'padded', None) is not None:
                try:
                    padded = dpdf.padded
                    self.paddingPlotPreview.updatePColorMeshPlot(padded[:,:,padded.shape[2]//2].transpose(), title="Padded Data")
                except Exception:
                    self._show_empty_preview(self.paddingPlotPreview, "Padding Preview (unable to render)")
            else:
                self._show_empty_preview(self.paddingPlotPreview, "Padding Preview (no padded data)")
        else:
            self._show_empty_preview(self.paddingPlotPreview, "Padding Preview (no padded data)")