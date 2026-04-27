# AP 2026
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QScrollArea
from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QSignalBlocker

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

from nxs_analysis_tools.datareduction import load_transform
from nexusformat.nexus import NXdata
from nxs_analysis_tools.pairdistribution import DeltaPDF


class _InlineTrimSegmentWidget(QGroupBox):
    removed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(self, axis_name: str, axis_values: np.ndarray, segment_number: int, parent=None):
        super().__init__(parent)
        self.axis_name = axis_name
        self.axis_values = np.asarray(axis_values)
        self.segment_number = segment_number

        self.setTitle(f"Segment {segment_number}")
        self._buildUi()
        self._updateLabels()

    def _buildUi(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Axis: {self.axis_name}"))

        self.startLabel = QLabel("")
        self.endLabel = QLabel("")

        self.startSlider = QSlider(Qt.Horizontal)
        self.startSlider.setRange(0, max(0, self.axis_values.size - 1))
        self.startSlider.setValue(0)
        self.startSlider.valueChanged.connect(self._onStartChanged)
        self.startSlider.sliderReleased.connect(self.changed.emit)

        self.endSlider = QSlider(Qt.Horizontal)
        self.endSlider.setRange(0, max(0, self.axis_values.size - 1))
        self.endSlider.setValue(max(0, self.axis_values.size - 1))
        self.endSlider.valueChanged.connect(self._onEndChanged)
        self.endSlider.sliderReleased.connect(self.changed.emit)

        layout.addWidget(QLabel("Start"))
        layout.addWidget(self.startSlider)
        layout.addWidget(self.startLabel)
        layout.addWidget(QLabel("End"))
        layout.addWidget(self.endSlider)
        layout.addWidget(self.endLabel)

        remove_row = QHBoxLayout()
        remove_row.addStretch(1)
        remove_btn = QPushButton("Remove Segment")
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        remove_row.addWidget(remove_btn)
        layout.addLayout(remove_row)

        self.setLayout(layout)

    def _onStartChanged(self, value: int):
        if value > self.endSlider.value():
            with QSignalBlocker(self.endSlider):
                self.endSlider.setValue(value)
        self._updateLabels()

    def _onEndChanged(self, value: int):
        if value < self.startSlider.value():
            with QSignalBlocker(self.startSlider):
                self.startSlider.setValue(value)
        self._updateLabels()

    def _updateLabels(self):
        s = self.startSlider.value()
        e = self.endSlider.value()
        self.startLabel.setText(f"Index {s}: {self.axis_values[s]:.6g}")
        self.endLabel.setText(f"Index {e}: {self.axis_values[e]:.6g}")

    def segment(self) -> tuple[int, int]:
        return self.startSlider.value(), self.endSlider.value()

class MainAnalysisPage(IAnalysisPage):
    openExtractedData = pyqtSignal(NXdata) # Signal to send extracted line cut data to the line cut page
    openDeltaPDF = pyqtSignal(DeltaPDF)
    
    def __init__(self, settings : QSettings):
        super().__init__(settings)
        self.extractedData = None
        self._trimmed_data: NXdata | None = None
        self._trim_axis_index: int = 0
        self._trim_segment_widgets: list[_InlineTrimSegmentWidget] = []
        self._trim_ui_initialized: bool = False
        
        self.initAdditionalUI()
        
        
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

        if self.additionalOptionsCombo.findText("Trim Data") < 0:
            self.additionalOptionsCombo.addItem("Trim Data")

        self.setLayout(self.layout)
        
    def onDataPathSelected(self, filePathTuple : tuple[str, list]):
        print(f"Data path selected: {filePathTuple}")
        # Save last directory
        last_directory = self.file_manager_widget.getFolderDataPath()
        self.settings.setValue('lastDirectory', last_directory)
        self.last_directory = last_directory
        
        # self.loadData(filePathTuple)
        self.loadTemperature(filePathTuple)
        
    def loadTemperature(self, filePathTuple : tuple[str, list]):
        # Placeholder for temperature loading logic
        print(f"Loading temperature info from: {filePathTuple[0]}")
        # data : NXdata = load_transform(filePathTuple[0])
        
        # self.dataModel = TemperatureDataModel(filePathTuple)
        self.dataModel = TemperatureDaskDataModel(filePathTuple)
        self.dataModel.setIndex(self.plotSliderWidget.value())
        
        self.file_manager_widget.populateTemperatureCombo(self.dataModel.getTemperatureValues())
        self.file_manager_widget.setFileOptionsEnabled(True)
        
            
    def onFileOptionsSubmit(self):
        print(f"File Options Widget Submitted changed: {self.file_manager_widget.getTemperatureComboValue()}")
        self.dataModel.setTemperature(self.file_manager_widget.getTemperatureComboValue())
        self.dataModel.setHKLPlane(self.file_manager_widget.getHKLPlaneComboValue())
        
        self.plotSliderWidget.setMaximum(self.dataModel.getMaxDepth())
        self.plotSliderWidget.setEnabled(True)
        self._resetTrimState()
        
        # self.preLoadPlotsOption.setEnabled(True)
        
        self.redrawPlot()

    def _resetTrimState(self):
        self._trimmed_data = None
        self._trim_segment_widgets = []
        self._trim_axis_index = 0

    def _getEffectiveCurrentData(self) -> NXdata | None:
        return self._trimmed_data if self._trimmed_data is not None else self.dataModel.getCurrentData()

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
            effective_data = self._getEffectiveCurrentData()
            if effective_data is not None and self._trimmed_data is not None:
                quad_mesh_data = self._getQuadMeshFromData(effective_data)
                if quad_mesh_data:
                    autoscale = bool(getattr(self, "_autoscale_next_redraw", True))
                    self._autoscale_next_redraw = True
                    self.plotted_graph_widget.updateQuadMeshPlot(dataTuple=quad_mesh_data, autoscale=autoscale)
                    self._applyCurrentContrastRamp()
                return

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

    def _clearAdditionalOptionsWidgets(self):
        for i in reversed(range(self.additionalOptionsLayout.count())):
            item = self.additionalOptionsLayout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                self.additionalOptionsLayout.removeWidget(widget)
                widget.setParent(None)

    def _getTrimSegments(self) -> list[tuple[int, int]]:
        return sorted(widget.segment() for widget in self._trim_segment_widgets)

    def _trimSegmentsAreValid(self) -> bool:
        segments = self._getTrimSegments()
        for prev, cur in zip(segments, segments[1:]):
            if cur[0] <= prev[1]:
                return False
        return True

    def _renumberTrimSegments(self):
        for idx, widget in enumerate(self._trim_segment_widgets, start=1):
            widget.segment_number = idx
            widget.setTitle(f"Segment {idx}")

    def _onTrimAxisChanged(self, index: int):
        self._trim_axis_index = index
        self._clearTrimSegments()

    def _clearTrimSegments(self):
        if not hasattr(self, 'trimSegmentsLayout'):
            return
        for widget in self._trim_segment_widgets:
            widget.setParent(None)
        self._trim_segment_widgets = []

    def _onRemoveTrimSegment(self, widget: _InlineTrimSegmentWidget):
        if widget in self._trim_segment_widgets:
            self._trim_segment_widgets.remove(widget)
            widget.setParent(None)
            self._renumberTrimSegments()

    def _addTrimSegment(self):
        base_data = self.dataModel.getCurrentData()
        if base_data is None:
            return

        axes_attr = base_data.attrs['axes']
        axis_names = [axes_attr] if isinstance(axes_attr, str) else list(axes_attr)
        axis_name = axis_names[self._trim_axis_index]
        axis_values = np.asarray(base_data[axis_name])
        if axis_values.size == 0:
            return

        segment_widget = _InlineTrimSegmentWidget(axis_name, axis_values, len(self._trim_segment_widgets) + 1, self)
        segment_widget.removed.connect(self._onRemoveTrimSegment)
        segment_widget.changed.connect(lambda: None)
        self._trim_segment_widgets.append(segment_widget)
        self.trimSegmentsLayout.insertWidget(self.trimSegmentsLayout.count() - 1, segment_widget)

    def _applyTrimSegments(self):
        print("applying trim segments")
        base_data = self.dataModel.getCurrentData()
        if base_data is None:
            return
        if not self._trim_segment_widgets:
            return
        if not self._trimSegmentsAreValid():
            print("Trim segments cannot overlap.")
            return

        self._trimmed_data = trimNXdataToAxisSegments(base_data, self._trim_axis_index, self._getTrimSegments())

        # Keep slider bounds consistent with whichever axis is currently sliced.
        slice_axis_index = self.dataModel.getSliceAxisIndex()
        max_depth = len(np.asarray(self._trimmed_data.nxaxes[slice_axis_index])) - 1
        max_depth = max(0, max_depth)
        self.plotSliderWidget.setMaximum(max_depth)
        if self.plotSliderWidget.value() > max_depth:
            self.plotSliderWidget.setValue(max_depth)
            
        print("finished applying trim segments")

        self.redrawPlot()

    def _returnToFullDataset(self):
        self._trimmed_data = None
        self.plotSliderWidget.setMaximum(self.dataModel.getMaxDepth())
        self.redrawPlot()

    def _buildTrimAdditionalOptions(self):
        base_data = self.dataModel.getCurrentData()
        trim_root = QWidget()
        trim_layout = QVBoxLayout(trim_root)

        trim_layout.addWidget(QLabel("Trim current dataset by adding non-overlapping keep ranges."))

        axis_row = QHBoxLayout()
        axis_row.addWidget(QLabel("Trim axis:"))
        self.trimAxisCombo = QComboBox()
        if base_data is not None:
            axes_attr = base_data.attrs['axes']
            axis_names = [axes_attr] if isinstance(axes_attr, str) else list(axes_attr)
            self.trimAxisCombo.addItems([str(name) for name in axis_names])
        self.trimAxisCombo.currentIndexChanged.connect(self._onTrimAxisChanged)
        axis_row.addWidget(self.trimAxisCombo)
        axis_row.addStretch(1)
        trim_layout.addLayout(axis_row)

        self.trimSegmentsContainer = QWidget()
        self.trimSegmentsLayout = QVBoxLayout(self.trimSegmentsContainer)
        self.trimSegmentsLayout.addStretch(1)
        trim_scroll = QScrollArea()
        trim_scroll.setWidgetResizable(True)
        trim_scroll.setWidget(self.trimSegmentsContainer)
        trim_layout.addWidget(trim_scroll)

        button_row = QHBoxLayout()
        add_btn = QPushButton("Add Segment")
        add_btn.clicked.connect(self._addTrimSegment)
        apply_btn = QPushButton("Submit Trims")
        apply_btn.clicked.connect(self._applyTrimSegments)
        return_btn = QPushButton("Return To Full Dataset")
        return_btn.clicked.connect(self._returnToFullDataset)
        button_row.addWidget(add_btn)
        button_row.addWidget(apply_btn)
        button_row.addWidget(return_btn)
        button_row.addStretch(1)
        trim_layout.addLayout(button_row)

        self._trim_axis_index = self.trimAxisCombo.currentIndex() if self.trimAxisCombo.count() else 0
        self._trim_ui_initialized = True
        return trim_root
            
                
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
            self._clearAdditionalOptionsWidgets()
        elif selected_option == "Change colormap":
            changeColormap = QComboBox()
            changeColormap.addItems(["viridis", "plasma", "inferno", "magma", "cividis"])
            changeColormap.currentIndexChanged.connect(lambda newCmap: self.changeColormap(changeColormap.currentText()))
            self._clearAdditionalOptionsWidgets()
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
            self._clearAdditionalOptionsWidgets()
            self.additionalOptionsLayout.addWidget(skewAngleLabel)
            self.additionalOptionsLayout.addWidget(skewAngleSlider)
        elif selected_option == "Trim Data":
            self._clearAdditionalOptionsWidgets()
            self.additionalOptionsLayout.addWidget(self._buildTrimAdditionalOptions())
            
            
    def onOpenDeltaPDFOptionsDialogue(self):
        print("Opening Delta PDF Options Dialogue...")
        current_data = self._getEffectiveCurrentData()
        if current_data is None:
            self.plotted_graph_widget.toggleDeltaPDFMode(False)
            return

        deltaPDFOptionsDialog = DeltaPDFOptionsWidget(current_data, self)
        if deltaPDFOptionsDialog.exec_() == QDialog.Accepted:
            print("Delta PDF options accepted")
            # Retrieve options from the dialog
            delta_pdf = deltaPDFOptionsDialog.getDeltaPDF()
            # print(f"Delta PDF options: {delta_pdf_options}")
            # Placeholder for applying delta PDF options
            self.openDeltaPDF.emit(delta_pdf)
        else:
            self.plotted_graph_widget.toggleDeltaPDFMode(False)
            


