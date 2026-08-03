# AP 2026
#extension of mainAnalysisPage.py, meant to load diffuse scattering data (without temperature?)

import os

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from CGTProject.pages.mainAnalysisPage import MainAnalysisPage
from CGTProject.models.diffuseScatteringModel import DiffuseDataModel
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget

from CGTProject.utilities.HKLPlaneEnum import HKLPlaneEnum

class DeltaPDFPage(MainAnalysisPage):
    def __init__(self, settings, dpdf):
        self.dpdf = dpdf
        super().__init__(settings)
        self.HKLPlane = HKLPlaneEnum.H_K_Plane
        # The redraw path reads the *model's* plane, not the page's, so push the
        # default down to the model explicitly. Guarantees getQuadMeshAtCurrentIndex
        # never short-circuits with "HKL Plane not set." for a freshly opened dpdf.
        if self.dataModel is not None and self.dataModel.getHKLPlane() is None:
            self.dataModel.setHKLPlane(self.HKLPlane)

        # Delta-PDF is signed data: follow the conventional diverging display --
        # blue-white-red with white pinned at zero. The colormap is re-applied on
        # every redraw (updateQuadMeshPlot recreates the mesh -> resets to viridis),
        # and contrast limits are held symmetric about zero.
        self._plotCmap = "bwr"  # blue -> white -> red; the delta-PDF default
        self._currentCmap = self._plotCmap  # active colormap; user may change it, reset restores _plotCmap
        self._useSymmetricContrast = True

        # The inherited FileManagerWidget auto-initializes from the last directory
        # (QTimer.singleShot in its constructor) and emits pathSelected, which would
        # run loadTemperature and REPLACE our DiffuseDataModel with a plane-less
        # TemperatureDaskDataModel -- breaking the slider ("HKL Plane not set.").
        # This page's data comes from the passed-in dpdf, so detach the file-loading
        # signals before the scheduled auto-init fires.
        for signal, handler in (
            (self.file_manager_widget.pathSelected, self.onDataPathSelected),
            (self.file_manager_widget.submitOptions, self.onFileOptionsSubmit),
        ):
            try:
                signal.disconnect(handler)
            except (TypeError, RuntimeError):
                pass
        # self.plotted_graph_widget = PlottedGraphWidget()

        self.dataModel.setIndex(self.plotSliderWidget.value())
        self.plotSliderWidget.setMaximum(self.dataModel.getMaxDepth())
        self.plotSliderWidget.setEnabled(True)
        
        #print the shape of the dpdf data
        if self.dpdf is not None:
            print(f"DeltaPDF data shape: {self.dpdf.data.shape}")
        else:
            print("DeltaPDF data is None.")
        
        #auto collapse file manager widget
        self.file_manager_widget._setCollapsed(True)
        self.redrawPlot()
        
    def setupDataModel(self):
        self.dataModel : DiffuseDataModel = DiffuseDataModel(self.dpdf) # Placeholder for DiffuseDataModel instance

    def redrawPlot(self):
        # Base redraw builds the mesh and applies the (symmetric) contrast ramp;
        # then re-apply the active colormap, since the mesh may have been recreated
        # (which resets the colormap back to matplotlib's default). Defaults to the
        # delta-PDF bwr map but respects a user's selection until they reset.
        super().redrawPlot()
        self._applyDeltaPdfColormap()

    def _applyDeltaPdfColormap(self):
        widget = getattr(self, "plotted_graph_widget", None)
        if widget is not None and getattr(widget, "quadmesh", None) is not None:
            widget.changeColorMap(self._currentCmap)

    def changeColormap(self, newCmap):
        # Remember the user's choice so redrawPlot keeps applying it (instead of
        # snapping back to bwr) until they reset to the delta-PDF default.
        self._currentCmap = newCmap
        super().changeColormap(newCmap)

    def _getColormapComboDefault(self) -> str:
        # Open the colormap combo on whatever is currently active (bwr by default).
        return self._currentCmap

    def _buildExtraColormapControls(self):
        resetButton = QPushButton(f"Reset to Delta-PDF default ({self._plotCmap})")
        resetButton.clicked.connect(self.resetColormapToDefault)
        self.additionalOptionsLayout.addWidget(resetButton)

    def resetColormapToDefault(self):
        self.changeColormap(self._plotCmap)
        combo = getattr(self, "_colormapCombo", None)
        if combo is not None:
            combo.blockSignals(True)
            combo.setCurrentText(self._plotCmap)
            combo.blockSignals(False)

    def _getActivePlotData(self):
        current_data = super()._getActivePlotData()
        if current_data is not None:
            return current_data

        if self.dpdf is None:
            return None

        return getattr(self.dpdf, "fft", None) or getattr(self.dpdf, "data", None)

    def _getExportNameTag(self) -> str:
        return "deltaPDF"

    def _getExportTemperature(self) -> str:
        current_data = self._getActivePlotData()
        if current_data is not None:
            source_temperature = str(current_data.attrs.get("source_temperature", "") or "").strip()
            if source_temperature:
                return source_temperature

        source_temperature = str(getattr(self.dpdf, "source_temperature", "") or "").strip()
        if source_temperature:
            return source_temperature

        return super()._getExportTemperature()

    def _afterSaveCurrentData(self, export_path: str, current_data):
        dat_path = os.path.splitext(export_path)[0] + ".dat"

        build_options = getattr(self.dpdf, "build_options", {}) or {}
        enabled_flags = {
            key: value
            for key, value in build_options.items()
            if isinstance(value, bool) and value
        }

        with open(dat_path, "w", encoding="utf-8") as dat_file:
            dat_file.write("# DeltaPDF build options\n")
            dat_file.write(f"source_nxs={export_path}\n")
            dat_file.write(f"source_temperature={getattr(self.dataModel, 'temperature', 'current')}\n")
            dat_file.write("\n")

            dat_file.write("[enabled_options]\n")
            if enabled_flags:
                for key in sorted(enabled_flags.keys()):
                    dat_file.write(f"{key}=true\n")
            else:
                dat_file.write("none=true\n")

            dat_file.write("\n[all_options]\n")
            if build_options:
                for key in sorted(build_options.keys()):
                    dat_file.write(f"{key}={build_options[key]}\n")
            else:
                dat_file.write("note=No DeltaPDF option metadata available for this object.\n")

        print(f"Saved DeltaPDF options to: {dat_path}")
    