# AP 2026
#extension of mainAnalysisPage.py, meant to load diffuse scattering data (without temperature?)

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from CGTProject.pages.mainAnalysisPage import MainAnalysisPage
from CGTProject.models.diffuseScatteringModel import DiffuseDataModel

class DeltaPDFPage(MainAnalysisPage):
    def __init__(self, settings):
        super().__init__(settings)
        # self.page_title.setText("Delta PDF Analysis")
    
    def loadData(self, filePathTuple : tuple[str, list]):
        # Placeholder for data loading logic
        print(f"Loading data from: {filePathTuple[0]}")
        # data : NXdata = load_transform(filePathTuple[0])
        self.diffuseDataModel = DiffuseDataModel(filePathTuple)
        
    #     self.classeDataModel.setIndex(self.plotSliderWidget.value())
        
    #     self.file_manager_widget.populateTemperatureCombo(self.classeDataModel.getTemperatureValues())
    #     self.file_manager_widget.setFileOptionsEnabled(True)
        
    # def onFileOptionsComboChanged(self):
    #     print(f"Temperature combo changed: {self.file_manager_widget.getTemperatureComboValue()}")
    #     # self.classeDataModel.setTemperature(self.file_manager_widget.getTemperatureComboValue())
    #     self.classeDataModel.setHKLPlane(self.file_manager_widget.getHKLPlaneComboValue())
        
    #     self.plotSliderWidget.setMaximum(self.classeDataModel.getMaxDepth())
    #     self.plotSliderWidget.setEnabled(True)
        
    #     # self.preLoadPlotsOption.setEnabled(True)
        
    #     self.redrawPlot()