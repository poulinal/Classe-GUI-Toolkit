# AP 2026
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSlider, QComboBox, QCheckBox
from PyQt5.QtCore import Qt, QSettings

from CGTProject.widgets.fileManagerWidget import FileManagerWidget
from CGTProject.models.classeDataModel import ClasseDataModel
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget

from nxs_analysis_tools.datareduction import load_transform
from nexusformat.nexus import NXdata

class MainAnalysisPage(QWidget):
    def __init__(self, settings : QSettings):
        super().__init__()
        self.settings = settings
        # Load last directory
        self.last_directory = self.settings.value('lastDirectory', '')
        
        self.initUI()
        
        self.classeDataModel = None # Placeholder for ClasseDataModel instance
        
    def initUI(self):
        layout = QVBoxLayout()
        label = QLabel("Main Analysis Page")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)
        
        self.file_manager_widget = FileManagerWidget(self.last_directory)
        self.file_manager_widget.pathSelected.connect(self.onDataPathSelected)
        
        self.back_btn = QPushButton("← Back to Main Menu")
        
        self.plotted_graph_widget = PlottedGraphWidget()
        self.plotSliderWidget = QSlider(Qt.Horizontal)
        self.plotSliderWidget.setMinimum(0)
        self.plotSliderWidget.setMaximum(100)
        self.plotSliderWidget.setValue(0)
        self.plotSliderWidget.setTickPosition(QSlider.TicksBelow)
        self.plotSliderWidget.setTickInterval(1)
        self.plotSliderWidget.setEnabled(False)
        
        self.plotSliderWidget.valueChanged.connect(self.onPlotSliderValueChanged)
        
        self.plottingDataOptions = QVBoxLayout()
        self.changeTemperatureCombo = QComboBox()
        self.changeTemperatureCombo.setEnabled(False)
        self.changeTemperatureCombo.currentIndexChanged.connect(self.onTemperatureComboChanged)
        self.plottingDataOptions.addWidget(QLabel("Select Temperature:"))
        self.plottingDataOptions.addWidget(self.changeTemperatureCombo)
        self.preLoadPlotsOption = QCheckBox("Pre-load all data into memory")
        self.preLoadPlotsOption.setEnabled(False)
        self.preLoadPlotsOption.stateChanged.connect(lambda state: self.onPreLoadPlotsOptionChanged(state))
        self.plottingDataOptions.addWidget(self.preLoadPlotsOption)
        
        layout.addStretch()
        layout.addWidget(self.file_manager_widget)
        layout.addLayout(self.plottingDataOptions)
        layout.addWidget(self.plotted_graph_widget)
        layout.addWidget(self.plotSliderWidget)
        layout.addWidget(self.back_btn)
        
        self.setLayout(layout)
        
    def onDataPathSelected(self, filePathTuple : tuple[str, list, list]):
        print(f"Data path selected: {filePathTuple}")
        # Save last directory
        self.settings.setValue('lastDirectory', filePathTuple[0])
        self.last_directory = filePathTuple[0]
        
        self.loadData(filePathTuple)
        
    def loadData(self, filePathTuple : tuple[str, list, list]):
        # Placeholder for data loading logic
        print(f"Loading data from: {filePathTuple[0]}")
        # data : NXdata = load_transform(filePathTuple[0])
        self.classeDataModel = ClasseDataModel(filePathTuple)
        self.classeDataModel.setIndex(self.plotSliderWidget.value())
        
        self.changeTemperatureCombo.addItems(self.classeDataModel.getTemperatureValues())
        self.changeTemperatureCombo.setEnabled(True)
        
        self.plotSliderWidget.setMaximum(len(self.classeDataModel.data[self.getTemperatureComboValue()].nxaxes[2]) - 1) ##TODO fix
        self.plotSliderWidget.setEnabled(True)
        
        # self.preLoadPlotsOption.setEnabled(True)
        
        self.classeDataModel.setTemperature(self.getTemperatureComboValue())
        
        self.redrawPlot()
        
        
    def onPlotSliderValueChanged(self, value):
        print(f"Plot slider value changed: {value}")
        self.classeDataModel.setIndex(value)
        self.redrawPlot()
            
    def onTemperatureComboChanged(self, index):
        print(f"Temperature combo changed: {index}")
        self.classeDataModel.setTemperature(self.getTemperatureComboValue())
        self.redrawPlot()
        
    def onPreLoadDataOptionChanged(self, state):
        if state == Qt.Checked:
            print("Pre-load all data option enabled")
            # Placeholder for pre-loading all data into memory
            # self.classeDataModel.preloadAllData()
        else:
            print("Pre-load all data option disabled")
            # Placeholder for disabling pre-loading
            # self.classeDataModel.unloadData()
    
    def getTemperatureComboValue(self):
        return self.changeTemperatureCombo.currentText()
        
    def redrawPlot(self):
        if self.classeDataModel:
            quad_mesh_data = self.classeDataModel.getQuadMeshAtCurrentIndex()
            if quad_mesh_data:
                self.plotted_graph_widget.updateQuadMeshPlot(quad_mesh_data)
                
    def initialPlot(self):
        if self.classeDataModel:
            quad_mesh_data = self.classeDataModel.getQuadMeshAtCurrentIndex()
            if quad_mesh_data:
                self.plotted_graph_widget.plotQuadMeshData(quad_mesh_data)
        
        
        