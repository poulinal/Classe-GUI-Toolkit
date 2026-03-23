# AP 2026
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QDialog, QVBoxLayout
from PyQt5.QtCore import Qt, QSettings, pyqtSignal

from abc import abstractmethod

from CGTProject.widgets.fileManagerWidget import FileManagerWidget
from CGTProject.models.temperatureDataModel import TemperatureDataModel
from CGTProject.models.dataModel import DataModel
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget
from CGTProject.widgets.plottedLineModesGraphWidget import PlottedLineModesGraphWidget
from CGTProject.widgets.lineCutOptionsDialogue import LineCutOptionsDialogue
from CGTProject.utilities.lineCutModeEnum import LineCutModeEnum
from CGTProject.widgets.deltaPDFOptionsDialogue import DeltaPDFOptionsWidget

from nxs_analysis_tools.datareduction import load_transform
from nexusformat.nexus import NXdata
from nxs_analysis_tools.pairdistribution import DeltaPDF

class IAnalysisPage(QWidget):
    def __init__(self, settings : QSettings):
        super().__init__()
        self.settings = settings
        # Load last directory
        self.last_directory = self.settings.value('lastDirectory', '')
        
        self.layout = QGridLayout()
        
        self.initUI()
        
        # self.dataModel : TemperatureDataModel = None # Placeholder for temperatureDataModel instance
        self.setupDataModel()
        
    @abstractmethod
    def setupDataModel(self):
        self.dataModel : DataModel = None
        
    def initUI(self):

        self.back_btn = QPushButton("← Back to Main Menu")
        self.layout.addWidget(self.back_btn, 6, 0, 1, 3)

        self.plotted_graph_widget = PlottedLineModesGraphWidget()
        self.layout.addWidget(self.plotted_graph_widget, 3, 0, 1, 2)

        self.plotSliderWidget = QSlider(Qt.Horizontal)
        self.plotSliderWidget.setMinimum(0)
        self.plotSliderWidget.setMaximum(100)
        self.plotSliderWidget.setValue(0)
        self.plotSliderWidget.setTickPosition(QSlider.TicksBelow)
        self.plotSliderWidget.setTickInterval(1)
        self.plotSliderWidget.setEnabled(False)
        self.plotSliderWidget.valueChanged.connect(self.onPlotSliderValueChanged)
        self.layout.addWidget(self.plotSliderWidget, 4, 0, 1, 2)

        self.additionalOptionsCombo = QComboBox()
        self.additionalOptionsCombo.addItems(["--", "Change colormap", "Skew Angle"])
        self.additionalOptionsCombo.setEnabled(True)
        self.additionalOptionsCombo.currentIndexChanged.connect(self.onAdditionalOptionChanged)
        self.layout.addWidget(self.additionalOptionsCombo, 2, 2, 1, 1)

        self.additionalOptionsLayout = QVBoxLayout()
        self.layout.addLayout(self.additionalOptionsLayout, 3, 2, 1, 1)

        self.setLayout(self.layout)
            
    def redrawPlot(self):
        if self.dataModel:
            quad_mesh_data = self.dataModel.getQuadMeshAtCurrentIndex()
            if quad_mesh_data:
                self.plotted_graph_widget.updateQuadMeshPlot(quad_mesh_data)
      
    def onPlotSliderValueChanged(self, value):
        print(f"Plot slider value changed: {value}")
        self.dataModel.setIndex(value)
        self.redrawPlot()
            
    def onAdditionalOptionChanged(self, index):
        selected_option = self.additionalOptionsCombo.currentText()
        print(f"Additional option selected: {selected_option}")
        if selected_option == "--":
            #clear previous options
            for i in reversed(range(self.additionalOptionsLayout.count())): 
                widgetToRemove = self.additionalOptionsLayout.itemAt(i).widget()
                self.additionalOptionsLayout.removeWidget(widgetToRemove)
                widgetToRemove.setParent(None)
        elif selected_option == "Change colormap":
            changeColormap = QComboBox()
            changeColormap.addItems(["viridis", "plasma", "inferno", "magma", "cividis"])
            changeColormap.currentIndexChanged.connect(lambda newCmap: self.changeColormap(changeColormap.currentText()))
            # Clear previous options            
            for i in reversed(range(self.additionalOptionsLayout.count())): 
                widgetToRemove = self.additionalOptionsLayout.itemAt(i).widget()
                self.additionalOptionsLayout.removeWidget(widgetToRemove)
                widgetToRemove.setParent(None)
            self.additionalOptionsLayout.addWidget(changeColormap)
        elif selected_option == "Skew Angle":
            skewAngleLabel = QLabel("Skew Angle:")
            skewAngleSlider = QSlider(Qt.Horizontal)
            skewAngleSlider.setMinimum(-45)
            skewAngleSlider.setMaximum(45)
            skewAngleSlider.setValue(0)
            skewAngleSlider.setTickPosition(QSlider.TicksBelow)
            skewAngleSlider.setTickInterval(1)
            #on release of slider 
            skewAngleSlider.sliderReleased.connect(lambda: self.applySkewAngle(skewAngleSlider.value()))
            # Clear previous options            
            for i in reversed(range(self.additionalOptionsLayout.count())): 
                widgetToRemove = self.additionalOptionsLayout.itemAt(i).widget()
                self.additionalOptionsLayout.removeWidget(widgetToRemove)
                widgetToRemove.setParent(None)
            self.additionalOptionsLayout.addWidget(skewAngleLabel)
            self.additionalOptionsLayout.addWidget(skewAngleSlider)
            
    def applySkewAngle(self, angle):
        print(f"Applying skew angle: {angle}")
        quadmesh = self.dataModel.updateSkewAngle(angle)
        self.plotted_graph_widget.updateQuadMeshPlot(quadmesh)
        
    def changeColormap(self, newCmap):
        print("Changing colormap...")
        # Placeholder for colormap change logic
        if self.plotted_graph_widget:
            self.plotted_graph_widget.changeColorMap("new_cmap")
            self.redrawPlot()


