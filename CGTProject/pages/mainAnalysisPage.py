# AP 2026
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QDialog, QVBoxLayout
from PyQt5.QtCore import Qt, QSettings, pyqtSignal

from CGTProject.widgets.fileManagerWidget import FileManagerWidget
from CGTProject.models.classeDataModel import ClasseDataModel
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget
from CGTProject.widgets.lineCutOptionsDialogue import LineCutOptionsDialogue
from CGTProject.utilities.lineCutModeEnum import LineCutModeEnum

from nxs_analysis_tools.datareduction import load_transform
from nexusformat.nexus import NXdata

class MainAnalysisPage(QWidget):
    openExtractedData = pyqtSignal(NXdata) # Signal to send extracted line cut data to the line cut page
    
    def __init__(self, settings : QSettings):
        super().__init__()
        self.settings = settings
        # Load last directory
        self.last_directory = self.settings.value('lastDirectory', '')
        self.extractedData = None
        
        self.initUI()
        
        self.classeDataModel : ClasseDataModel = None # Placeholder for ClasseDataModel instance
        
    def initUI(self):
        
        layout = QGridLayout()
        label = QLabel("Main Analysis Page")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label, 0, 0, 1, 2)
        
        self.file_manager_widget = FileManagerWidget(self.last_directory)
        self.file_manager_widget.pathSelected.connect(self.onDataPathSelected)
        self.file_manager_widget.submitOptions.connect(self.onFileOptionsComboChanged)
        layout.addWidget(self.file_manager_widget, 1, 0, 1, 3)

        self.back_btn = QPushButton("← Back to Main Menu")
        layout.addWidget(self.back_btn, 6, 0, 1, 3)

        self.plotted_graph_widget = PlottedGraphWidget()
        self.plotted_graph_widget.lineCutModeActivated.connect(self.onLineCutModeActivated)
        layout.addWidget(self.plotted_graph_widget, 3, 0, 1, 2)

        self.plotSliderWidget = QSlider(Qt.Horizontal)
        self.plotSliderWidget.setMinimum(0)
        self.plotSliderWidget.setMaximum(100)
        self.plotSliderWidget.setValue(0)
        self.plotSliderWidget.setTickPosition(QSlider.TicksBelow)
        self.plotSliderWidget.setTickInterval(1)
        self.plotSliderWidget.setEnabled(False)
        self.plotSliderWidget.valueChanged.connect(self.onPlotSliderValueChanged)
        layout.addWidget(self.plotSliderWidget, 4, 0, 1, 2)

        self.additionalOptionsCombo = QComboBox()
        self.additionalOptionsCombo.addItems(["--", "Change colormap", "Skew Angle"])
        self.additionalOptionsCombo.setEnabled(True)
        self.additionalOptionsCombo.currentIndexChanged.connect(self.onAdditionalOptionChanged)
        layout.addWidget(self.additionalOptionsCombo, 2, 2, 1, 1)

        self.additionalOptionsLayout = QVBoxLayout()
        layout.addLayout(self.additionalOptionsLayout, 3, 2, 1, 1)

        self.plottingDataOptions = QVBoxLayout()
        self.preLoadPlotsOption = QCheckBox("Pre-load all data into memory")
        self.preLoadPlotsOption.setEnabled(False)
        self.preLoadPlotsOption.stateChanged.connect(lambda state: self.onPreLoadDataOptionChanged(state))
        self.plottingDataOptions.addWidget(self.preLoadPlotsOption)
        layout.addLayout(self.plottingDataOptions, 2, 0, 1, 1)

        self.plotSubmitVLineCut = QPushButton("Submit Verticle Line Cut")
        self.plotSubmitVLineCut.setEnabled(False)
        self.plotSubmitVLineCut.clicked.connect(lambda : self.onSubmitLineCut(verticle=True))

        self.plotSubmitHLineCut = QPushButton("Submit Horizontal Line Cut")
        self.plotSubmitHLineCut.setEnabled(False)
        self.plotSubmitHLineCut.clicked.connect(lambda : self.onSubmitLineCut(verticle=False))

        layout.addWidget(self.plotSubmitVLineCut, 5, 0, 1, 1)
        layout.addWidget(self.plotSubmitHLineCut, 5, 1, 1, 1)

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
        
        self.file_manager_widget.populateTemperatureCombo(self.classeDataModel.getTemperatureValues())
        self.file_manager_widget.setFileOptionsEnabled(True)
        
        
    def onPlotSliderValueChanged(self, value):
        print(f"Plot slider value changed: {value}")
        self.classeDataModel.setIndex(value)
        self.redrawPlot()
            
    def onFileOptionsComboChanged(self):
        print(f"Temperature combo changed: {self.file_manager_widget.getTemperatureComboValue()}")
        self.classeDataModel.setTemperature(self.file_manager_widget.getTemperatureComboValue())
        self.classeDataModel.setHKLPlane(self.file_manager_widget.getHKLPlaneComboValue())
        
        self.plotSliderWidget.setMaximum(self.classeDataModel.getMaxDepth())
        self.plotSliderWidget.setEnabled(True)
        
        # self.preLoadPlotsOption.setEnabled(True)
        
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
            
    def onLineCutModeActivated(self):
        if self.plotted_graph_widget.getLineCutMode() == LineCutModeEnum.VERTICAL:
            print("Line Cut Mode Activated: Vertical")
            self.plotSubmitVLineCut.setEnabled(True)
        elif self.plotted_graph_widget.getLineCutMode() == LineCutModeEnum.HORIZONTAL:
            print("Line Cut Mode Activated: Horizontal")
            self.plotSubmitHLineCut.setEnabled(True)
        elif self.plotted_graph_widget.getLineCutMode() == LineCutModeEnum.BOTH:
            print("Line Cut Mode Activated: Both")
            self.plotSubmitVLineCut.setEnabled(True)
            self.plotSubmitHLineCut.setEnabled(True)
        
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
                
    def onSubmitLineCut(self, verticle : bool):
        print("Submit Line Cut button clicked")
        # Placeholder for line cut submission logic
        lineCutOptionsDialog = LineCutOptionsDialogue(self.classeDataModel.getHKLPlane(), mousePos = self.plotted_graph_widget.getMousePoint(), currentData = self.classeDataModel.getCurrentData(), dataAxisMinMax=(self.classeDataModel.getDataAxisMinMax(0), self.classeDataModel.getDataAxisMinMax(1), self.classeDataModel.getDataAxisMinMax(2)), dataAxisResolutions=(self.classeDataModel.getDataAxisResolution(0), self.classeDataModel.getDataAxisResolution(1), self.classeDataModel.getDataAxisResolution(2)))
        
        if lineCutOptionsDialog.exec_() == QDialog.Accepted:
            print("Line cut options accepted")
            # Retrieve line cut options from the dialog
            line_cut_options = lineCutOptionsDialog.getLineCutOptions()
            print(f"Line cut options: {line_cut_options}")
            # Apply line cut options to the data model
            extractedData = self.classeDataModel.applyLineCutOptions(line_cut_options, self.plotted_graph_widget.getMousePoint(), verticle)
            if extractedData:
                self.openExtractedData.emit(extractedData)
            else:
                ValueError("No data extracted from line cut options")
            
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
        quadmesh = self.classeDataModel.updateSkewAngle(angle)
        self.plotted_graph_widget.updateQuadMeshPlot(quadmesh)
        
    def changeColormap(self, newCmap):
        print("Changing colormap...")
        # Placeholder for colormap change logic
        if self.plotted_graph_widget:
            self.plotted_graph_widget.changeColorMap("new_cmap")
            self.redrawPlot()


