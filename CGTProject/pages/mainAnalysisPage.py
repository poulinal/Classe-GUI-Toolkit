# AP 2026
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QScrollArea, QProgressBar, QApplication, QMessageBox
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
import os

import numpy as np

from CGTProject.widgets.fileManagerWidget import FileManagerWidget
from CGTProject.models.temperatureDataModel import TemperatureDataModel
from CGTProject.models.temperatureDaskDataModel import TemperatureDaskDataModel
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget
from CGTProject.widgets.plottedLineModesGraphWidget import PlottedLineModesGraphWidget
from CGTProject.widgets.lineCutOptionsDialogue import LineCutOptionsDialogue
from CGTProject.utilities.lineCutModeEnum import LineCutModeEnum
from CGTProject.utilities.HKLPlaneEnum import HKLPlaneEnum
from CGTProject.widgets.deltaPDFOptionsDialogue import DeltaPDFOptionsWidget
from CGTProject.pages.iAnalysisPage import IAnalysisPage
from CGTProject.utilities.NXDataHandler import trimNXdataToAxisSegments
from CGTProject.utilities.additionalOptionsEnum import AdditionalOptionsEnum
from CGTProject.widgets.trimDataWidget import TrimDataWidget, _InlineTrimSegmentWidget
from CGTProject.widgets.binDataWidget import BinDataWidget
from CGTProject.utilities.dataStorageWarningEnum import DataStorageWarningEnum


from nxs_analysis_tools.datareduction import load_transform
from nexusformat.nexus import NXdata, nxload
from nxs_analysis_tools.pairdistribution import DeltaPDF

class MainAnalysisPage(IAnalysisPage):
    openExtractedData = pyqtSignal(NXdata) # Signal to send extracted line cut data to the line cut page
    openDeltaPDF = pyqtSignal(DeltaPDF)
    
    def __init__(self, settings : QSettings):
        super().__init__(settings)
        self.extractedData = None
        self._trim_axis_index: int = 0
        self._trim_segment_widgets: list[_InlineTrimSegmentWidget] = []
        self._trim_ui_initialized: bool = False
        
        self.initAdditionalUI()

    def _banner_manager(self):
        return getattr(self, "banner_manager", None)

    def _notify_info(self, message: str):
        banner_manager = self._banner_manager()
        if banner_manager is not None:
            banner_manager.show_info(message)

    def _notify_success(self, message: str):
        banner_manager = self._banner_manager()
        if banner_manager is not None:
            banner_manager.show_success(message)

    def _notify_warning(self, message: str):
        banner_manager = self._banner_manager()
        if banner_manager is not None:
            banner_manager.show_warning(message)

    def _notify_error(self, message: str):
        banner_manager = self._banner_manager()
        if banner_manager is not None:
            banner_manager.show_error(message)
        
        
    def setupDataModel(self):
        # self.dataModel : TemperatureDataModel = None # Placeholder for temperatureDataModel instance
        self.dataModel : TemperatureDaskDataModel = None # Placeholder for temperatureDataModel instance
        
    def initAdditionalUI(self):
    
        label = QLabel("Main Analysis Page")
        label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(label, 0, 0, 1, 2)
        
        self.file_manager_widget = FileManagerWidget(self.last_directory)
        self.file_manager_widget.pathSelected.connect(self.onDataPathSelected)
        self.file_manager_widget.submitOptions.connect(self.onFileOptionsSubmit)
        self.layout.addWidget(self.file_manager_widget, 1, 0, 1, 3)

        self.loadProgressBar = QProgressBar()
        self.loadProgressBar.setRange(0, 100)
        self.loadProgressBar.setVisible(False)
        self.layout.addWidget(self.loadProgressBar, 12, 0, 1, 3)

        # self.back_btn = QPushButton("← Back to Main Menu")
        # self.layout.addWidget(self.back_btn, 6, 0, 1, 3)

        self.plotted_graph_widget.lineCutModeActivated.connect(self.onLineCutModeActivated)
        self.plotted_graph_widget.openDeltaPDFOptionsDialogue.connect(self.onOpenDeltaPDFOptionsDialogue)
        self.layout.addWidget(self.plotted_graph_widget, 3, 0, 1, 2)

        self.plottingDataOptions = QVBoxLayout()
        self.preLoadPlotsOption = QCheckBox("Pre-load all data into memory")
        self.preLoadPlotsOption.setEnabled(False)
        self.preLoadPlotsOption.stateChanged.connect(lambda state: self.onPreLoadDataOptionChanged(state))
        self.plottingDataOptions.addWidget(self.preLoadPlotsOption)
        self.layout.addLayout(self.plottingDataOptions, 2, 0, 1, 1)

        self.plotSubmitVLineCut = QPushButton("Submit Vertical Line Cut")
        self.plotSubmitVLineCut.setEnabled(False)
        self.plotSubmitVLineCut.clicked.connect(lambda : self.onSubmitLineCut(verticle=True))

        self.plotSubmitHLineCut = QPushButton("Submit Horizontal Line Cut")
        self.plotSubmitHLineCut.setEnabled(False)
        self.plotSubmitHLineCut.clicked.connect(lambda : self.onSubmitLineCut(verticle=False))

        self.layout.addWidget(self.plotSubmitVLineCut, 5, 0, 1, 1)
        self.layout.addWidget(self.plotSubmitHLineCut, 5, 1, 1, 1)
        
        self.dataUsageLabel = QLabel() #be wary we're only updating this during redrawPlot, could do via signal to make it easier during mutations of data without redraw.
        self.layout.addWidget(self.dataUsageLabel, 11, 0, 1, 2)

        # if self.additionalOptionsCombo.findText(str(AdditionalOptionsEnum.TRIM_DATA)) < 0:
        #     self.additionalOptionsCombo.addItem(str(AdditionalOptionsEnum.TRIM_DATA))

        self.setLayout(self.layout)

    def _setLoadProgress(self, percent: int, message: str = ""):
        self.loadProgressBar.setVisible(True)
        self.loadProgressBar.setValue(max(0, min(100, percent)))
        self.loadProgressBar.setFormat(f"{message} %p%" if message else "%p%")
        QApplication.processEvents()

    def _finishLoadProgress(self):
        self.loadProgressBar.setValue(100)
        self.loadProgressBar.setVisible(False)
        self.loadProgressBar.setFormat("%p%")
        QApplication.processEvents()
        
    def onDataPathSelected(self, filePathTuple : tuple[str, list]):
        print(f"Data path selected: {filePathTuple}")
        self._notify_info(f"Data path selected: {filePathTuple[0]}")
        # Save last directory
        last_directory = self.file_manager_widget.getFolderDataPath()
        self.settings.setValue('lastDirectory', last_directory)
        self.last_directory = last_directory
        
        # self.loadData(filePathTuple)
        self.loadTemperature(filePathTuple)
        
    def loadTemperature(self, filePathTuple : tuple[str, list]):
        # Placeholder for temperature loading logic
        print(f"Loading temperature info from: {filePathTuple[0]}")
        self._notify_info(f"Loading temperature info from: {filePathTuple[0]}")
        # data : NXdata = load_transform(filePathTuple[0])
        
        # self.dataModel = TemperatureDataModel(filePathTuple)
        self.dataModel = TemperatureDaskDataModel(filePathTuple)
        self.dataModel.setIndex(self.plotSliderWidget.value())
        
        if hasattr(self.dataModel, "getTemperatureDisplayEntries"):
            self.file_manager_widget.populateTemperatureCombo(self.dataModel.getTemperatureDisplayEntries())
        else:
            self.file_manager_widget.populateTemperatureCombo(self.dataModel.getTemperatureValues())
        self.file_manager_widget.setFileOptionsEnabled(True)
        
            
    def onFileOptionsSubmit(self):
        print(f"File Options Widget Submitted changed: {self.file_manager_widget.getTemperatureComboValue()}")
        self._notify_info("Applying file options and loading data")

        selected_metadata_path = self.file_manager_widget.getTemperatureComboValue()
        if not os.path.isabs(selected_metadata_path) and hasattr(self.dataModel, "build_metadata_path"):
            metadata_path = self.dataModel.build_metadata_path(selected_metadata_path)
            if metadata_path:
                selected_metadata_path = metadata_path

        # If the selected file is a saved DeltaPDF export, open it directly in DeltaPDFPage.
        if selected_metadata_path and "deltapdf" in os.path.basename(selected_metadata_path).lower():
            try:
                fft_data = nxload(selected_metadata_path).entry.transform
                dpdf = DeltaPDF()
                dpdf.fft = fft_data
                dpdf.source_temperature = self._extractTemperatureFromPath(selected_metadata_path)
                dpdf.source_data_path_root = getattr(self.dataModel, "dataPathRoot", "")
                try:
                    dpdf.fft.attrs["source_temperature"] = dpdf.source_temperature
                    dpdf.fft.attrs["source_data_path_root"] = getattr(self.dataModel, "dataPathRoot", "")
                except Exception:
                    pass
                dpdf.build_options = {}
                self.openDeltaPDF.emit(dpdf)
                self._notify_success(f"Opened DeltaPDF file: {os.path.basename(metadata_path)}")
                return
            except Exception as exc:
                self._notify_error(f"Failed to open DeltaPDF file: {exc}")
                return

        try:
            self._setLoadProgress(0, "Loading data")
            if hasattr(self.dataModel, "setMetadataPath"):
                self.dataModel.setMetadataPath(
                    selected_metadata_path,
                    progress_callback=self._setLoadProgress,
                )
            else:
                self.dataModel.setTemperature(
                    self._extractTemperatureFromPath(selected_metadata_path),
                    progress_callback=self._setLoadProgress,
                )
            self.dataModel.setHKLPlane(self.file_manager_widget.getHKLPlaneComboValue())
        
            self.plotSliderWidget.setMaximum(self.dataModel.getMaxDepth())
            self.plotSliderWidget.setEnabled(True)
            self._resetTrimState()

            # self.preLoadPlotsOption.setEnabled(True)

            self.redrawPlot()
            self._notify_success("Finished loading temperature data")
        finally:
            self._finishLoadProgress()

    def _resetTrimState(self):
        self._trim_segment_widgets = []
        self._trim_axis_index = 0

    def _getQuadMeshFromData(self, nxdata: NXdata) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        if nxdata is None or self.dataModel.HKLPlane is None:
            return None

        signal_name = nxdata.attrs['signal']
        signal = np.asarray(nxdata[signal_name])
        axes_attr = nxdata.attrs['axes']
        axis_names = [axes_attr] if isinstance(axes_attr, str) else list(axes_attr)
        axes = [np.asarray(nxdata[name]) for name in axis_names]

        if self.dataModel.HKLPlane == HKLPlaneEnum.H_K_Plane:
            if len(axes) < 3:
                return None
            x = axes[0]
            y = axes[1]
            idx = min(max(0, self.plotSliderWidget.value()), signal.shape[2] - 1)
            c = np.asarray(signal[:, :, idx]).T
        elif self.dataModel.HKLPlane == HKLPlaneEnum.H_L_Plane:
            if len(axes) < 3:
                return None
            x = axes[0]
            y = axes[2]
            idx = min(max(0, self.plotSliderWidget.value()), signal.shape[1] - 1)
            c = np.asarray(signal[:, idx, :]).T
        elif self.dataModel.HKLPlane == HKLPlaneEnum.K_L_Plane:
            if len(axes) < 3:
                return None
            x = axes[1]
            y = axes[2]
            idx = min(max(0, self.plotSliderWidget.value()), signal.shape[0] - 1)
            c = np.asarray(signal[idx, :, :]).T
        else:
            return None

        return x, y, c
        
    def onPreLoadDataOptionChanged(self, state):
        if state == Qt.Checked:
            print("Pre-load all data option enabled")
            self._notify_info("Pre-load all data option enabled")
            # Placeholder for pre-loading all data into memory
            # self.dataModel.preloadAllData()
        else:
            print("Pre-load all data option disabled")
            self._notify_warning("Pre-load all data option disabled")
            # Placeholder for disabling pre-loading
            # self.dataModel.unloadData()
            
    def onLineCutModeActivated(self):
        if self.plotted_graph_widget.getLineCutMode() == LineCutModeEnum.VERTICAL:
            print("Line Cut Mode Activated: Vertical")
            self._notify_info("Line cut mode activated: Vertical")
            self.plotSubmitVLineCut.setEnabled(True)
        elif self.plotted_graph_widget.getLineCutMode() == LineCutModeEnum.HORIZONTAL:
            print("Line Cut Mode Activated: Horizontal")
            self._notify_info("Line cut mode activated: Horizontal")
            self.plotSubmitHLineCut.setEnabled(True)
        elif self.plotted_graph_widget.getLineCutMode() == LineCutModeEnum.BOTH:
            print("Line Cut Mode Activated: Both")
            self._notify_info("Line cut mode activated: Both")
            self.plotSubmitVLineCut.setEnabled(True)
            self.plotSubmitHLineCut.setEnabled(True)
        
    def redrawPlot(self):
        if self.dataModel:
            quad_mesh_data = self.dataModel.getQuadMeshAtCurrentIndex()
            if quad_mesh_data:
                # print(f"quadmeshdata: {quad_mesh_data}")
                autoscale = bool(getattr(self, "_autoscale_next_redraw", True))
                self._autoscale_next_redraw = True
                if isinstance(self.dataModel, TemperatureDaskDataModel):
                    print("Data model is TemperatureDaskDataModel, updating plot with new quad mesh data")
                    self.plotted_graph_widget.updateQuadMeshPlot(dataTuple=quad_mesh_data, autoscale=autoscale)
                elif isinstance(self.dataModel, TemperatureDataModel):
                    print("Data model is TemperatureDataModel, updating plot with new quad mesh data")
                    self.plotted_graph_widget.updateQuadMeshPlot(dataQuadMesh=quad_mesh_data, autoscale=autoscale)
                else:
                    print(f"Data model is {type(self.dataModel).__name__}, updating plot with new quad mesh data")
                    if isinstance(quad_mesh_data, tuple) and len(quad_mesh_data) == 3:
                        self.plotted_graph_widget.updateQuadMeshPlot(dataTuple=quad_mesh_data, autoscale=autoscale)
                    else:
                        self.plotted_graph_widget.updateQuadMeshPlot(dataQuadMesh=quad_mesh_data, autoscale=autoscale)
                self._applyCurrentContrastRamp()
                
                self.updateDataStorageLabel()
                
    def updateDataStorageLabel(self):
        dataUsage = self.dataModel.dataStorageUsage # in bytes
        unit = 'bytes'
        
        if dataUsage > DataStorageWarningEnum.CRITICAL:
            # If data usage is greater than 25 GB, display in red
            colorWarning = 'color: red;'
            self.dataUsageLabel.setStyleSheet(colorWarning)
        elif dataUsage > DataStorageWarningEnum.WARNING:
            # If data usage is greater than 5 GB, display in orange
            colorWarning = 'color: orange;'
            self.dataUsageLabel.setStyleSheet(colorWarning)
        else:
            colorWarning = 'color: green;'
            self.dataUsageLabel.setStyleSheet(colorWarning)
        
        if dataUsage > 1e6:
            dataUsageConverted = dataUsage / 1e6
            unit = 'MB'
        elif dataUsage > 1e9:
            dataUsageConverted = dataUsage / 1e9
            unit = 'GB'
            
            
        self.dataUsageLabel.setText(f"Data Storage Usage: {dataUsageConverted:.2f} {unit}")

    def _clearAdditionalOptionsWidgets(self):
        for i in reversed(range(self.additionalOptionsLayout.count())):
            item = self.additionalOptionsLayout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                self.additionalOptionsLayout.removeWidget(widget)
                widget.setParent(None)

    def _extractTemperatureFromPath(self, metadata_path: str) -> str:
        base_name = os.path.basename(metadata_path)
        for suffix in ("_standalone_hkl.nxs", "_standalone_native.nxs", ".nxs"):
            if base_name.endswith(suffix):
                base_name = base_name[: -len(suffix)]
                break

        for token in reversed(base_name.split("_")):
            if token.replace(".", "", 1).isdigit():
                return token
        return "current"
            
                
    def onSubmitLineCut(self, verticle : bool):
        print("Submit Line Cut button clicked")
        self._notify_info("Submitting line cut")
        # Placeholder for line cut submission logic
        lineCutOptionsDialog = LineCutOptionsDialogue(self.dataModel.getHKLPlane(), mousePos = self.plotted_graph_widget.getMousePoint(), currentData = self.dataModel.getCurrentData(), dataAxisMinMax=(self.dataModel.getDataAxisMinMax(0), self.dataModel.getDataAxisMinMax(1), self.dataModel.getDataAxisMinMax(2)), dataAxisResolutions=(self.dataModel.getDataAxisResolution(0), self.dataModel.getDataAxisResolution(1), self.dataModel.getDataAxisResolution(2)))
        
        if lineCutOptionsDialog.exec_() == QDialog.Accepted:
            print("Line cut options accepted")
            self._notify_success("Line cut options accepted")
            # Retrieve line cut options from the dialog
            line_cut_options = lineCutOptionsDialog.getLineCutOptions()
            print(f"Line cut options: {line_cut_options}")
            # Apply line cut options to the data model
            extractedData = self.dataModel.applyLineCutOptions(line_cut_options, self.plotted_graph_widget.getMousePoint(), verticle)
            if extractedData:
                self.openExtractedData.emit(extractedData)
            else:
                self._notify_error("No data extracted from line cut options")
                ValueError("No data extracted from line cut options")
            
    def onAdditionalOptionChanged(self, index):
        selected_option = self.additionalOptionsCombo.itemText(index) if index >= 0 else self.additionalOptionsCombo.currentText()
        print(f"Additional option selected: {selected_option}")
        if selected_option == AdditionalOptionsEnum.BLANK_STATE.value:
            self._clearAdditionalOptionsWidgets()
        elif selected_option == AdditionalOptionsEnum.CHANGE_COLORMAP.value:
            changeColormap = QComboBox()
            changeColormap.addItems(["viridis", "plasma", "inferno", "magma", "cividis"])
            changeColormap.currentIndexChanged.connect(lambda newCmap: self.changeColormap(changeColormap.currentText()))
            self._clearAdditionalOptionsWidgets()
            self.additionalOptionsLayout.addWidget(changeColormap)
        elif selected_option == AdditionalOptionsEnum.SKEW_DATA.value:
            skewAngleLabel = QLabel("Skew Angle:")
            skewAngleSlider = QSlider(Qt.Horizontal)
            skewAngleSlider.setMinimum(-45)
            skewAngleSlider.setMaximum(45)
            skewAngleSlider.setValue(0)
            skewAngleSlider.setTickPosition(QSlider.TicksBelow)
            skewAngleSlider.setTickInterval(1)
            #on release of slider 
            skewAngleSlider.sliderReleased.connect(lambda: self.applySkewAngle(skewAngleSlider.value()))
            self._clearAdditionalOptionsWidgets()
            self.additionalOptionsLayout.addWidget(skewAngleLabel)
            self.additionalOptionsLayout.addWidget(skewAngleSlider)
        elif selected_option == AdditionalOptionsEnum.TRIM_DATA.value:
            self._clearAdditionalOptionsWidgets()
            self.trimDataWidget = TrimDataWidget(dataModel = self.dataModel, file_manager_widget = self.file_manager_widget, plot_slider_widget = self.plotSliderWidget, parent=self)
            self.trimDataWidget.notifyInfo.connect(self._notify_info)
            self.trimDataWidget.notifySuccess.connect(self._notify_success)
            self.trimDataWidget.notifyWarning.connect(self._notify_warning)
            self.trimDataWidget.notifyError.connect(self._notify_error)
            self.trimDataWidget.progressChanged.connect(self._setLoadProgress)
            self.trimDataWidget.progressFinished.connect(self._finishLoadProgress)
            self.trimDataWidget.redrawRequested.connect(self.redrawPlot)
            self.additionalOptionsLayout.addWidget(self.trimDataWidget._buildTrimAdditionalOptions())
        elif selected_option == AdditionalOptionsEnum.BIN_DATA.value:
            self._clearAdditionalOptionsWidgets()
            self.binDataWidget = BinDataWidget(dataModel = self.dataModel, file_manager_widget = self.file_manager_widget, plot_slider_widget = self.plotSliderWidget, parent=self)
            self.binDataWidget.notifyInfo.connect(self._notify_info)
            self.binDataWidget.notifySuccess.connect(self._notify_success)
            self.binDataWidget.notifyWarning.connect(self._notify_warning)
            self.binDataWidget.notifyError.connect(self._notify_error)
            self.binDataWidget.progressChanged.connect(self._setLoadProgress)
            self.binDataWidget.progressFinished.connect(self._finishLoadProgress)
            self.binDataWidget.redrawRequested.connect(self.redrawPlot)
            self.additionalOptionsLayout.addWidget(self.binDataWidget._buildBinAdditionalOptions())
        else:
            super().onAdditionalOptionChanged(index)
            
            
    def onOpenDeltaPDFOptionsDialogue(self):
        print("Opening Delta PDF Options Dialogue...")
        
        print("First checking data usage")
        if self.dataModel.dataStorageUsage > DataStorageWarningEnum.CRITICAL:
            QMessageBox.warning(
                self,
                "Data Storage CRITICAL Warning",
                "CRITICAL WARNING. Data storage usage is VERY high. It is HIGHLY recommended to reduce data size before attempting a deltaPDF analysis. Please reduce data via trim/binning before proceeding with Delta PDF options."
            )
            
            # return
        elif self.dataModel.dataStorageUsage > DataStorageWarningEnum.WARNING:
            QMessageBox.warning(
                self,
                "Data Storage Warning",
                "Data storage usage is high. It is recommended to reduce data size below 1Gb before preforming a deltaPDF. Proceed with caution when opening Delta PDF options."
            )
        
        
        
        
        self._notify_info("Opening Delta PDF options")
        current_data = self.dataModel.getCurrentData()
        if current_data is None:
            self.plotted_graph_widget.toggleDeltaPDFMode(False)
            return

        deltaPDFOptionsDialog = DeltaPDFOptionsWidget(current_data, self)
        if deltaPDFOptionsDialog.exec_() == QDialog.Accepted:
            print("Delta PDF options accepted")
            self._notify_success("Delta PDF options accepted")
            # Retrieve options from the dialog
            delta_pdf = deltaPDFOptionsDialog.getDeltaPDF()
            delta_pdf.source_temperature = getattr(self.dataModel, "temperature", "")
            delta_pdf.source_data_path_root = getattr(self.dataModel, "dataPathRoot", "")
            delta_pdf.build_options = deltaPDFOptionsDialog.getBuildOptions()
            try:
                delta_pdf.fft.attrs["source_temperature"] = getattr(self.dataModel, "temperature", "")
                delta_pdf.fft.attrs["source_data_path_root"] = getattr(self.dataModel, "dataPathRoot", "")
            except Exception:
                pass
            # print(f"Delta PDF options: {delta_pdf_options}")
            # Placeholder for applying delta PDF options
            self.openDeltaPDF.emit(delta_pdf)
        else:
            self.plotted_graph_widget.toggleDeltaPDFMode(False)
            


