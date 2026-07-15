# AP 2026
#extension of mainAnalysisPage.py, meant to load diffuse scattering data (without temperature?)

import os

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from CGTProject.pages.mainAnalysisPage import MainAnalysisPage
from CGTProject.models.diffuseScatteringModel import DiffuseDataModel
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget

from CGTProject.utilities.HKLPlaneEnum import HKLPlaneEnum

class DeltaPDFPage(MainAnalysisPage):
    def __init__(self, settings, dpdf):
        self.dpdf = dpdf
        super().__init__(settings)
        self.HKLPlane = HKLPlaneEnum.H_K_Plane
        # self.plotted_graph_widget = PlottedGraphWidget()
        
        self.dataModel.setIndex(self.plotSliderWidget.value())
        self.plotSliderWidget.setMaximum(self.dataModel.getMaxDepth())
        self.plotSliderWidget.setEnabled(True)
        
        #print the shape of the dpdf data
        if self.dpdf is not None:
            print(f"DeltaPDF data shape: {self.dpdf.data.shape}")
        else:
            print("DeltaPDF data is None.")
        
        self.redrawPlot()
        
    def setupDataModel(self):
        self.dataModel : DiffuseDataModel = DiffuseDataModel(self.dpdf) # Placeholder for DiffuseDataModel instance

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
    