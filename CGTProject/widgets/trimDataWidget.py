# AP 2026

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QScrollArea, QSlider, QGroupBox
from PyQt5.QtCore import pyqtSignal, QSignalBlocker, QTimer, Qt

import numpy as np

from CGTProject.utilities.NXDataHandler import trimNXdataToAxisSegments


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
    



class TrimDataWidget(QWidget):
    notifyInfo = pyqtSignal(str)
    notifySuccess = pyqtSignal(str)
    notifyWarning = pyqtSignal(str)
    notifyError = pyqtSignal(str)
    progressChanged = pyqtSignal(int, str)
    progressFinished = pyqtSignal()
    redrawRequested = pyqtSignal()

    def __init__(self, dataModel, file_manager_widget, plot_slider_widget, parent=None):
        super().__init__(parent)
        self.dataModel = dataModel
        self.file_manager_widget = file_manager_widget
        self.plotSliderWidget = plot_slider_widget

        self._trim_segment_widgets: list[_InlineTrimSegmentWidget] = []
        self._trim_axis_index: int = 0
        self._trim_ui_initialized: bool = False
    
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
        self.notifyInfo.emit("Starting trim operation")
        try:
            self.progressChanged.emit(0, "Trimming data")
            base_data = self.dataModel.getCurrentData()
            if base_data is None:
                return
            if not self._trim_segment_widgets:
                return
            if not self._trimSegmentsAreValid():
                print("Trim segments cannot overlap.")
                self.notifyWarning.emit("Trim segments cannot overlap.")
                return

            self.progressChanged.emit(25, "Processing segments")
            trimmed_data = trimNXdataToAxisSegments(base_data, self._trim_axis_index, self._getTrimSegments())
            self.progressChanged.emit(75, "Applying trimmed data")
            self.dataModel.replaceCurrentData(trimmed_data)

            # Keep slider bounds consistent with the active dataset.
            self.progressChanged.emit(85, "Updating display")
            slice_axis_index = self.dataModel.getSliceAxisIndex()
            max_depth = len(np.asarray(self.dataModel.getCurrentData().nxaxes[slice_axis_index])) - 1
            max_depth = max(0, max_depth)
            self.plotSliderWidget.setMaximum(max_depth)
            if self.plotSliderWidget.value() > max_depth:
                self.plotSliderWidget.setValue(max_depth)

            print("finished applying trim segments")
            self.notifySuccess.emit("Finished applying trim segments")

            self.redrawRequested.emit()
        finally:
            self.progressFinished.emit()

    def _returnToFullDataset(self):
        self.notifyInfo.emit("Reloading full dataset")
        try:
            self.progressChanged.emit(0, "Reloading full dataset")
            progress_cb = lambda percent, message="": self.progressChanged.emit(percent, message)
            if hasattr(self.dataModel, "reloadCurrentData"):
                self.dataModel.reloadCurrentData(progress_callback=progress_cb)
            else:
                self.dataModel.setTemperature(
                    self.file_manager_widget.getTemperatureComboValue(),
                    progress_callback=progress_cb,
                )
            self.plotSliderWidget.setMaximum(self.dataModel.getMaxDepth())
            self.plotSliderWidget.setEnabled(True)
            self.redrawRequested.emit()
            self.notifySuccess.emit("Full dataset reloaded")
        finally:
            self.progressFinished.emit()

    def _buildTrimAdditionalOptions(self): #TODO put into separate widget and child functions -- already have trim widget as dialogue, repurpose
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