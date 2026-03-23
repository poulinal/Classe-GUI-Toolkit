# AP 2026
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QDialog, QVBoxLayout
from PyQt5.QtCore import Qt, QSettings, pyqtSignal

from CGTProject.widgets.fileManagerWidget import FileManagerWidget
from CGTProject.models.temperatureDataModel import TemperatureDataModel
from CGTProject.models.temperatureDaskDataModel import TemperatureDaskDataModel
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget
from CGTProject.widgets.plottedLineModesGraphWidget import PlottedLineModesGraphWidget
from CGTProject.widgets.lineCutOptionsDialogue import LineCutOptionsDialogue
from CGTProject.utilities.lineCutModeEnum import LineCutModeEnum
from CGTProject.widgets.deltaPDFOptionsDialogue import DeltaPDFOptionsWidget
from CGTProject.pages.iAnalysisPage import IAnalysisPage

from nxs_analysis_tools.datareduction import load_transform
from nexusformat.nexus import NXdata
from nxs_analysis_tools.pairdistribution import DeltaPDF

class MainAnalysisPage(IAnalysisPage):
    openExtractedData = pyqtSignal(NXdata) # Signal to send extracted line cut data to the line cut page
    openDeltaPDF = pyqtSignal(DeltaPDF)
    
    def __init__(self, settings : QSettings):
        super().__init__(settings)
        self.extractedData = None
        
        self.initAdditionalUI()
        
        
    def setupDataModel(self):
        self.dataModel : TemperatureDataModel = None # Placeholder for temperatureDataModel instance
        # self.dataModel : TemperatureDaskDataModel = None # Placeholder for temperatureDataModel instance
        
    def initAdditionalUI(self):
    
        label = QLabel("Main Analysis Page")
        label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(label, 0, 0, 1, 2)
        
        self.file_manager_widget = FileManagerWidget(self.last_directory)
        self.file_manager_widget.pathSelected.connect(self.onDataPathSelected)
        self.file_manager_widget.submitOptions.connect(self.onFileOptionsSubmit)
        self.layout.addWidget(self.file_manager_widget, 1, 0, 1, 3)

        self.back_btn = QPushButton("← Back to Main Menu")
        self.layout.addWidget(self.back_btn, 6, 0, 1, 3)

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

        self.setLayout(self.layout)
        
    def onDataPathSelected(self, filePathTuple : tuple[str, list]):
        print(f"Data path selected: {filePathTuple}")
        # Save last directory
        self.settings.setValue('lastDirectory', filePathTuple[0])
        self.last_directory = filePathTuple[0]
        
        # self.loadData(filePathTuple)
        self.loadTemperature(filePathTuple)
        
    def loadTemperature(self, filePathTuple : tuple[str, list]):
        # Placeholder for temperature loading logic
        print(f"Loading temperature info from: {filePathTuple[0]}")
        # data : NXdata = load_transform(filePathTuple[0])
        self.dataModel = TemperatureDataModel(filePathTuple)
        # self.dataModel = TemperatureDaskDataModel(filePathTuple)
        self.dataModel.setIndex(self.plotSliderWidget.value())
        
        self.file_manager_widget.populateTemperatureCombo(self.dataModel.getTemperatureValues())
        self.file_manager_widget.setFileOptionsEnabled(True)
        
            
    def onFileOptionsSubmit(self):
        print(f"File Options Widget Submitted changed: {self.file_manager_widget.getTemperatureComboValue()}")
        self.dataModel.setTemperature(self.file_manager_widget.getTemperatureComboValue())
        self.dataModel.setHKLPlane(self.file_manager_widget.getHKLPlaneComboValue())
        
        self.plotSliderWidget.setMaximum(self.dataModel.getMaxDepth())
        self.plotSliderWidget.setEnabled(True)
        
        # self.preLoadPlotsOption.setEnabled(True)
        
        self.redrawPlot()
        
    def onPreLoadDataOptionChanged(self, state):
        if state == Qt.Checked:
            print("Pre-load all data option enabled")
            # Placeholder for pre-loading all data into memory
            # self.dataModel.preloadAllData()
        else:
            print("Pre-load all data option disabled")
            # Placeholder for disabling pre-loading
            # self.dataModel.unloadData()
            
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
        if self.dataModel:
            quad_mesh_data = self.dataModel.getQuadMeshAtCurrentIndex()
            if quad_mesh_data:
                print(f"quadmeshdata: {quad_mesh_data}")
                self.plotted_graph_widget.updateQuadMeshPlot(quad_mesh_data)
            
                
    def onSubmitLineCut(self, verticle : bool):
        print("Submit Line Cut button clicked")
        # Placeholder for line cut submission logic
        lineCutOptionsDialog = LineCutOptionsDialogue(self.dataModel.getHKLPlane(), mousePos = self.plotted_graph_widget.getMousePoint(), currentData = self.dataModel.getCurrentData(), dataAxisMinMax=(self.dataModel.getDataAxisMinMax(0), self.dataModel.getDataAxisMinMax(1), self.dataModel.getDataAxisMinMax(2)), dataAxisResolutions=(self.dataModel.getDataAxisResolution(0), self.dataModel.getDataAxisResolution(1), self.dataModel.getDataAxisResolution(2)))
        
        if lineCutOptionsDialog.exec_() == QDialog.Accepted:
            print("Line cut options accepted")
            # Retrieve line cut options from the dialog
            line_cut_options = lineCutOptionsDialog.getLineCutOptions()
            print(f"Line cut options: {line_cut_options}")
            # Apply line cut options to the data model
            extractedData = self.dataModel.applyLineCutOptions(line_cut_options, self.plotted_graph_widget.getMousePoint(), verticle)
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
            
            
    def onOpenDeltaPDFOptionsDialogue(self):
        print("Opening Delta PDF Options Dialogue...")
        deltaPDFOptionsDialog = DeltaPDFOptionsWidget(self.dataModel.getCurrentData())
        if deltaPDFOptionsDialog.exec_() == QDialog.Accepted:
            print("Delta PDF options accepted")
            # Retrieve options from the dialog
            delta_pdf = deltaPDFOptionsDialog.getDeltaPDF()
            # print(f"Delta PDF options: {delta_pdf_options}")
            # Placeholder for applying delta PDF options
            self.openDeltaPDF.emit(delta_pdf)
        else:
            self.plotted_graph_widget.toggleDeltaPDFMode(False)
            


