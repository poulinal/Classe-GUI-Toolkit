# AP 2026
#extension of mainAnalysisPage.py, meant to load diffuse scattering data (without temperature?)

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
        
        self.redrawPlot()
        
    def setupDataModel(self):
        self.dataModel : DiffuseDataModel = DiffuseDataModel(self.dpdf) # Placeholder for DiffuseDataModel instance
    