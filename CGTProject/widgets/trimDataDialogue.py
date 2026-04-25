# AP 2026
from __future__ import annotations

from typing import Optional

import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal, QSignalBlocker, QObject, QThread, QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from nexusformat.nexus import NXdata

from CGTProject.utilities.NXDataHandler import trimNXdataToAxisSegments
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget


def _compute_quadmesh_payload(
    data: NXdata,
    axis_names: list[str],
    x_axis_index: int,
    slice_index: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str, str] | None:
    signal_name = data.attrs["signal"]
    signal = np.asarray(data[signal_name], dtype=float)
    if signal.ndim < 2:
        return None

    slice_axis_index = x_axis_index if signal.ndim == 2 else next(
        (idx for idx in range(signal.ndim - 1, -1, -1) if idx != x_axis_index),
        None,
    )
    if slice_axis_index == x_axis_index:
        slice_axis_index = None

    y_candidates = [idx for idx in range(signal.ndim) if idx not in (x_axis_index, slice_axis_index)]
    if y_candidates:
        y_axis_index = y_candidates[0]
    else:
        y_axis_index = 1 if x_axis_index == 0 and signal.ndim > 1 else 0

    working = signal
    active_axes = list(range(signal.ndim))

    if slice_axis_index is not None and slice_axis_index in active_axes:
        slice_pos = active_axes.index(slice_axis_index)
        max_slice = max(0, working.shape[slice_pos] - 1)
        clamped_index = min(max(0, int(slice_index)), max_slice)
        working = np.take(working, indices=clamped_index, axis=slice_pos)
        active_axes.pop(slice_pos)

    while len(active_axes) > 2:
        reduce_axis = next((idx for idx in active_axes if idx not in (x_axis_index, y_axis_index)), None)
        if reduce_axis is None:
            break
        reduce_pos = active_axes.index(reduce_axis)
        working = np.nanmean(np.abs(working), axis=reduce_pos)
        active_axes.pop(reduce_pos)

    if x_axis_index not in active_axes or y_axis_index not in active_axes:
        return None

    x_pos = active_axes.index(x_axis_index)
    y_pos = active_axes.index(y_axis_index)
    z_values = np.moveaxis(working, (y_pos, x_pos), (0, 1))

    x_name = axis_names[x_axis_index]
    y_name = axis_names[y_axis_index]
    x_values = np.asarray(data[x_name], dtype=float)
    y_values = np.asarray(data[y_name], dtype=float)

    if z_values.shape != (y_values.size, x_values.size):
        return None

    return x_values, y_values, z_values, x_name, y_name


class _TrimPlotLoadWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        nxdata: NXdata,
        axis_names: list[str],
        current_axis_index: int,
        full_slice_index: int,
        preview_slice_index: int,
        segments: list[tuple[int, int]],
        keep_whole: bool,
    ):
        super().__init__()
        self._nxdata = nxdata
        self._axis_names = axis_names
        self._current_axis_index = current_axis_index
        self._full_slice_index = full_slice_index
        self._preview_slice_index = preview_slice_index
        self._segments = segments
        self._keep_whole = keep_whole

    def run(self):
        try:
            full_mesh = _compute_quadmesh_payload(
                self._nxdata,
                self._axis_names,
                self._current_axis_index,
                self._full_slice_index,
            )

            preview_data = self._nxdata
            if not self._keep_whole and self._segments:
                preview_data = trimNXdataToAxisSegments(
                    self._nxdata,
                    self._current_axis_index,
                    self._segments,
                )

            preview_mesh = _compute_quadmesh_payload(
                preview_data,
                self._axis_names,
                self._current_axis_index,
                self._preview_slice_index,
            )

            self.finished.emit({"full_mesh": full_mesh, "preview_mesh": preview_mesh})
        except Exception as exc:
            self.failed.emit(str(exc))


class _TrimSegmentWidget(QGroupBox):
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
        remove_button = QPushButton("Remove Segment")
        remove_button.clicked.connect(lambda: self.removed.emit(self))
        remove_row.addWidget(remove_button)
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
        start_index = self.startSlider.value()
        end_index = self.endSlider.value()
        self.startLabel.setText(f"Index {start_index}: {self.axis_values[start_index]:.6g}")
        self.endLabel.setText(f"Index {end_index}: {self.axis_values[end_index]:.6g}")

    def segment(self) -> tuple[int, int]:
        return self.startSlider.value(), self.endSlider.value()


class TrimDataDialogue(QDialog):
    def __init__(self, nxdata: NXdata, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trim Data")
        self.setModal(True)
        self.resize(1200, 850)

        self.nxdata = nxdata
        axes_attr = nxdata.attrs["axes"]
        self.axis_names = [axes_attr] if isinstance(axes_attr, str) else list(axes_attr)
        self.current_axis_index = 0
        self._slice_axis_index: Optional[int] = None
        self._segment_widgets: list[_TrimSegmentWidget] = []
        self._trimmed_data: Optional[NXdata] = None
        self._plots_ready = False
        self._plot_load_in_progress = False
        self._plot_load_thread: Optional[QThread] = None
        self._plot_load_worker: Optional[_TrimPlotLoadWorker] = None
        self._plot_update_timer = QTimer(self)
        self._plot_update_timer.setSingleShot(True)
        self._plot_update_timer.timeout.connect(self._updatePlots)

        self._buildUi()
        self._refreshAxisData()
        self._updateControlsEnabled(self.keepWholeCheckBox.isChecked())
        QTimer.singleShot(0, self._startInitialPlotLoad)

    def _buildUi(self):
        layout = QVBoxLayout()

        title = QLabel("Choose a trim axis and keep one or more non-overlapping ranges.")
        title.setWordWrap(True)
        layout.addWidget(title)

        self.keepWholeCheckBox = QCheckBox("Keep the whole dataset")
        self.keepWholeCheckBox.setChecked(True)
        self.keepWholeCheckBox.toggled.connect(self._updateControlsEnabled)
        layout.addWidget(self.keepWholeCheckBox)

        axis_row = QHBoxLayout()
        axis_row.addWidget(QLabel("Trim axis:"))
        self.axisComboBox = QComboBox()
        self.axisComboBox.addItems(self.axis_names)
        self.axisComboBox.currentIndexChanged.connect(self._onAxisChanged)
        axis_row.addWidget(self.axisComboBox)
        axis_row.addStretch(1)
        layout.addLayout(axis_row)

        self.axisInfoLabel = QLabel("")
        layout.addWidget(self.axisInfoLabel)

        self.loadingLabel = QLabel("Loading plot previews...")
        self.loadingLabel.setVisible(False)
        layout.addWidget(self.loadingLabel)

        self.loadingBar = QProgressBar()
        self.loadingBar.setRange(0, 0)
        self.loadingBar.setVisible(False)
        layout.addWidget(self.loadingBar)

        plots_row = QHBoxLayout()
        self.fullDataPlotWidget = PlottedGraphWidget(self)
        self.trimPreviewPlotWidget = PlottedGraphWidget(self)
        self.fullDataPlotWidget.customToolbar.setVisible(False)
        self.trimPreviewPlotWidget.customToolbar.setVisible(False)
        self.fullDataPlotWidget.setMinimumHeight(260)
        self.trimPreviewPlotWidget.setMinimumHeight(260)
        self.fullDataPlotWidget.setMaximumHeight(360)
        self.trimPreviewPlotWidget.setMaximumHeight(360)
        plots_row.addWidget(self.fullDataPlotWidget, 1)
        plots_row.addWidget(self.trimPreviewPlotWidget, 1)
        layout.addLayout(plots_row, 2)

        self.fullSliceInfoLabel = QLabel("")
        layout.addWidget(self.fullSliceInfoLabel)
        self.fullSliceSlider = QSlider(Qt.Horizontal)
        self.fullSliceSlider.setMinimum(0)
        self.fullSliceSlider.setMaximum(0)
        self.fullSliceSlider.valueChanged.connect(lambda _: self._updateSliceInfoLabels())
        self.fullSliceSlider.sliderReleased.connect(self._schedulePlotUpdate)
        layout.addWidget(self.fullSliceSlider)

        self.previewSliceInfoLabel = QLabel("")
        layout.addWidget(self.previewSliceInfoLabel)
        self.previewSliceSlider = QSlider(Qt.Horizontal)
        self.previewSliceSlider.setMinimum(0)
        self.previewSliceSlider.setMaximum(0)
        self.previewSliceSlider.valueChanged.connect(lambda _: self._updateSliceInfoLabels())
        self.previewSliceSlider.sliderReleased.connect(self._schedulePlotUpdate)
        layout.addWidget(self.previewSliceSlider)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.segmentContainer = QWidget()
        self.segmentLayout = QVBoxLayout(self.segmentContainer)
        self.segmentLayout.addStretch(1)
        self.scrollArea.setWidget(self.segmentContainer)
        layout.addWidget(self.scrollArea, 3)

        button_row = QHBoxLayout()
        self.addSegmentButton = QPushButton("Add Segment")
        self.addSegmentButton.clicked.connect(self.addSegment)
        button_row.addWidget(self.addSegmentButton)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self._acceptSelection)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        action_row.addWidget(self.okButton)
        action_row.addWidget(self.cancelButton)
        layout.addLayout(action_row)

        self.setLayout(layout)

    def _refreshAxisData(self):
        self.current_axis_index = self.axisComboBox.currentIndex()
        self.axisInfoLabel.setText(self._defaultAxisInfoText())
        self._clearSegments()
        self._configureSliceSliders()
        if self._plots_ready:
            self._schedulePlotUpdate()

    def _schedulePlotUpdate(self):
        if not self._plots_ready or self._plot_load_in_progress:
            return
        self._plot_update_timer.start(80)

    def _startInitialPlotLoad(self):
        if self._plot_load_in_progress or self._plots_ready:
            return

        self._plot_load_in_progress = True
        self._setPlotLoading(True)

        thread = QThread(self)
        worker = _TrimPlotLoadWorker(
            self.nxdata,
            self.axis_names,
            self.current_axis_index,
            self.fullSliceSlider.value(),
            self.previewSliceSlider.value(),
            self._currentSegments(),
            self.keepWholeCheckBox.isChecked(),
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._onInitialPlotLoadFinished)
        worker.failed.connect(self._onInitialPlotLoadFailed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)

        self._plot_load_thread = thread
        self._plot_load_worker = worker
        thread.start()

    def _setPlotLoading(self, loading: bool):
        self.loadingLabel.setVisible(loading)
        self.loadingBar.setVisible(loading)
        for widget in (
            self.axisComboBox,
            self.keepWholeCheckBox,
            self.fullSliceSlider,
            self.previewSliceSlider,
            self.addSegmentButton,
            self.okButton,
        ):
            widget.setEnabled(not loading and (widget is not self.addSegmentButton or not self.keepWholeCheckBox.isChecked()))

    def _onInitialPlotLoadFinished(self, payload: dict):
        self._plot_load_in_progress = False
        self._plots_ready = True
        self._setPlotLoading(False)
        self._renderPlotPayload(payload)

    def _onInitialPlotLoadFailed(self, msg: str):
        self._plot_load_in_progress = False
        self.loadingLabel.setText(f"Plot preview load failed: {msg}")
        self.loadingBar.setVisible(False)
        self._plots_ready = True
        self._setPlotLoading(False)
        self._updatePlots()

    def _defaultAxisInfoText(self) -> str:
        axis_name = self.axis_names[self.current_axis_index]
        axis_values = np.asarray(self.nxdata[axis_name])
        if axis_values.size:
            return f"{axis_name}: {axis_values.size} points from {axis_values.min():.6g} to {axis_values.max():.6g}"
        return f"{axis_name}: no points available"

    def _configureSliceSliders(self):
        signal_name = self.nxdata.attrs["signal"]
        signal_field = self.nxdata[signal_name]
        signal_shape = tuple(getattr(signal_field, "shape", ()))
        signal_ndim = len(signal_shape)

        if signal_ndim < 3:
            self._slice_axis_index = None
            for slider in (self.fullSliceSlider, self.previewSliceSlider):
                slider.setEnabled(False)
                slider.setRange(0, 0)
                slider.setValue(0)
            self.fullSliceInfoLabel.setText("Full plot slice: not needed (2D data)")
            self.previewSliceInfoLabel.setText("Preview slice: not needed (2D data)")
            return

        candidates = [i for i in range(signal_ndim) if i != self.current_axis_index]
        if not candidates:
            self._slice_axis_index = None
            for slider in (self.fullSliceSlider, self.previewSliceSlider):
                slider.setEnabled(False)
                slider.setRange(0, 0)
                slider.setValue(0)
            self.fullSliceInfoLabel.setText("Full plot slice: unavailable")
            self.previewSliceInfoLabel.setText("Preview slice: unavailable")
            return

        self._slice_axis_index = candidates[-1]
        slice_axis_name = self.axis_names[self._slice_axis_index]
        slice_values = np.asarray(self.nxdata[slice_axis_name])
        max_index = max(0, slice_values.size - 1)

        self.fullSliceSlider.setEnabled(max_index > 0)
        self.previewSliceSlider.setEnabled(max_index > 0)
        self.fullSliceSlider.setRange(0, max_index)
        self.previewSliceSlider.setRange(0, max_index)
        self.fullSliceSlider.setValue(min(self.fullSliceSlider.value(), max_index))
        self.previewSliceSlider.setValue(min(self.previewSliceSlider.value(), max_index))

        self._updateSliceInfoLabels()

    def _updateSliceInfoLabels(self):
        if self._slice_axis_index is None:
            return

        slice_axis_name = self.axis_names[self._slice_axis_index]
        slice_values = np.asarray(self.nxdata[slice_axis_name])
        if slice_values.size == 0:
            self.fullSliceInfoLabel.setText(f"Full plot slice axis: {slice_axis_name} | no values")
            self.previewSliceInfoLabel.setText(f"Preview slice axis: {slice_axis_name} | no values")
            return

        full_idx = min(self.fullSliceSlider.value(), slice_values.size - 1)
        preview_idx = min(self.previewSliceSlider.value(), slice_values.size - 1)
        self.fullSliceInfoLabel.setText(
            f"Full plot slice axis: {slice_axis_name} | index {full_idx} | value {slice_values[full_idx]:.6g}"
        )
        self.previewSliceInfoLabel.setText(
            f"Preview slice axis: {slice_axis_name} | index {preview_idx} | value {slice_values[preview_idx]:.6g}"
        )

    def _quadMeshForData(self, data: NXdata, slice_index: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, str, str] | None:
        signal_name = data.attrs["signal"]
        signal = np.asarray(data[signal_name], dtype=float)
        if signal.ndim < 2:
            return None

        x_axis = self.current_axis_index
        slice_axis = self._slice_axis_index if self._slice_axis_index is not None and self._slice_axis_index < signal.ndim else None
        if slice_axis == x_axis:
            slice_axis = None

        y_candidates = [i for i in range(signal.ndim) if i != x_axis and i != slice_axis]
        y_axis = y_candidates[0] if y_candidates else (1 if x_axis == 0 and signal.ndim > 1 else 0)

        working = signal
        active_axes = list(range(signal.ndim))

        if slice_axis is not None and slice_axis in active_axes:
            slice_pos = active_axes.index(slice_axis)
            max_slice = max(0, working.shape[slice_pos] - 1)
            clamped_index = min(max(0, int(slice_index)), max_slice)
            working = np.take(working, indices=clamped_index, axis=slice_pos)
            active_axes.pop(slice_pos)

        while len(active_axes) > 2:
            reduce_axis = next((idx for idx in active_axes if idx not in (x_axis, y_axis)), None)
            if reduce_axis is None:
                break
            reduce_pos = active_axes.index(reduce_axis)
            working = np.nanmean(np.abs(working), axis=reduce_pos)
            active_axes.pop(reduce_pos)

        if x_axis not in active_axes or y_axis not in active_axes:
            return None

        x_pos = active_axes.index(x_axis)
        y_pos = active_axes.index(y_axis)
        z_values = np.moveaxis(working, (y_pos, x_pos), (0, 1))

        x_name = self.axis_names[x_axis]
        y_name = self.axis_names[y_axis]
        x_values = np.asarray(data[x_name], dtype=float)
        y_values = np.asarray(data[y_name], dtype=float)

        if z_values.shape != (y_values.size, x_values.size):
            return None

        return x_values, y_values, z_values, x_name, y_name

    def _currentSegments(self) -> list[tuple[int, int]]:
        return sorted(widget.segment() for widget in self._segment_widgets)

    def _isSegmentSelectionValid(self) -> bool:
        segments = self._currentSegments()
        for previous, current in zip(segments, segments[1:]):
            if current[0] <= previous[1]:
                return False
        return True

    def _updatePlots(self):
        if not self._plots_ready:
            return

        self._renderPlotPayload(self._buildPlotPayload())

    def _buildPlotPayload(self) -> dict:
        return {
            "full_mesh": _compute_quadmesh_payload(
                self.nxdata,
                self.axis_names,
                self.current_axis_index,
                self.fullSliceSlider.value(),
            ),
            "preview_mesh": _compute_quadmesh_payload(
                self.nxdata if self.keepWholeCheckBox.isChecked() or not self._segment_widgets else trimNXdataToAxisSegments(
                    self.nxdata,
                    self.current_axis_index,
                    self._currentSegments(),
                ),
                self.axis_names,
                self.current_axis_index,
                self.previewSliceSlider.value(),
            ),
        }

    def _draw_mesh_without_colorbar(
        self,
        plot_widget: PlottedGraphWidget,
        mesh: tuple[np.ndarray, np.ndarray, np.ndarray, str, str] | None,
        *,
        title: str,
        segment_spans: list[tuple[float, float]] | None = None,
        empty_message: str = "Quadmesh preview requires 2D or higher data.",
    ):
        axis = plot_widget.ax_main
        axis.clear()
        plot_widget._reset_colorbar()

        if mesh is None:
            axis.set_title(title)
            axis.text(
                0.5,
                0.5,
                empty_message,
                ha="center",
                va="center",
                transform=axis.transAxes,
            )
            plot_widget.canvas_main.draw_idle()
            return

        x_values, y_values, z_values, x_label, y_label = mesh
        axis.pcolormesh(x_values, y_values, z_values, shading="auto")
        axis.set_title(title)
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)

        if segment_spans:
            for x0, x1 in segment_spans:
                axis.axvspan(min(x0, x1), max(x0, x1), color="red", alpha=0.25)

        plot_widget.canvas_main.draw_idle()

    def _renderPlotPayload(self, payload: dict):
        self._updateSliceInfoLabels()

        full_mesh = payload.get("full_mesh")
        full_segment_spans = None
        if full_mesh is not None and not self.keepWholeCheckBox.isChecked() and self._segment_widgets:
            x_full = full_mesh[0]
            full_segment_spans = []
            for start_index, end_index in self._currentSegments():
                x0 = x_full[min(start_index, x_full.size - 1)]
                x1 = x_full[min(end_index, x_full.size - 1)]
                full_segment_spans.append((float(x0), float(x1)))

        self._draw_mesh_without_colorbar(
            self.fullDataPlotWidget,
            full_mesh,
            title="Dataset Slice",
            segment_spans=full_segment_spans,
        )

        if not self.keepWholeCheckBox.isChecked() and self._segment_widgets and not self._isSegmentSelectionValid():
            self._draw_mesh_without_colorbar(
                self.trimPreviewPlotWidget,
                None,
                title="Trim Preview",
                empty_message="Preview unavailable:\nsegments overlap.",
            )
            return

        preview_mesh = payload.get("preview_mesh")
        self._draw_mesh_without_colorbar(
            self.trimPreviewPlotWidget,
            preview_mesh,
            title="Trim Preview",
        )

    def _clearSegments(self):
        for widget in self._segment_widgets:
            widget.setParent(None)
        self._segment_widgets = []

    def _onAxisChanged(self, index: int):
        self.current_axis_index = index
        self._refreshAxisData()

    def _updateControlsEnabled(self, keep_whole: bool):
        if not self._plots_ready:
            return
        self.axisComboBox.setEnabled(not keep_whole)
        self.addSegmentButton.setEnabled(not keep_whole)
        for widget in self._segment_widgets:
            widget.setEnabled(not keep_whole)
        self._updateSegmentValidation()

    def addSegment(self):
        axis_name = self.axis_names[self.current_axis_index]
        axis_values = np.asarray(self.nxdata[axis_name])
        if axis_values.size == 0:
            return

        segment_widget = _TrimSegmentWidget(axis_name, axis_values, len(self._segment_widgets) + 1, self)
        segment_widget.removed.connect(self._removeSegment)
        segment_widget.changed.connect(self._updateSegmentValidation)
        self._segment_widgets.append(segment_widget)
        self.segmentLayout.insertWidget(self.segmentLayout.count() - 1, segment_widget)
        self.keepWholeCheckBox.setChecked(False)
        self._updateControlsEnabled(False)
        self._updateSegmentValidation()

    def _removeSegment(self, widget: _TrimSegmentWidget):
        if widget in self._segment_widgets:
            self._segment_widgets.remove(widget)
            widget.setParent(None)
            self._renumberSegments()
        self._updateSegmentValidation()

    def _renumberSegments(self):
        for idx, widget in enumerate(self._segment_widgets, start=1):
            widget.segment_number = idx
            widget.setTitle(f"Segment {idx}")

    def _updateSegmentValidation(self):
        if not self._plots_ready:
            return
        if self.keepWholeCheckBox.isChecked() or len(self._segment_widgets) <= 1:
            self.okButton.setEnabled(True)
            self.axisInfoLabel.setText(self._defaultAxisInfoText())
            self._schedulePlotUpdate()
            return

        segments = self._currentSegments()
        for previous, current in zip(segments, segments[1:]):
            if current[0] <= previous[1]:
                self.okButton.setEnabled(False)
                self.axisInfoLabel.setText("Segments cannot overlap. Adjust the ranges before continuing.")
                self._schedulePlotUpdate()
                return

        self.okButton.setEnabled(True)
        self.axisInfoLabel.setText(self._defaultAxisInfoText())
        self._schedulePlotUpdate()

    def closeEvent(self, event):
        if self._plot_load_thread is not None and self._plot_load_thread.isRunning():
            self._plot_load_thread.quit()
            self._plot_load_thread.wait(2000)
        super().closeEvent(event)

    def _acceptSelection(self):
        if self.keepWholeCheckBox.isChecked() or not self._segment_widgets:
            self._trimmed_data = self.nxdata
            self.accept()
            return

        segments = self._currentSegments()
        for previous, current in zip(segments, segments[1:]):
            if current[0] <= previous[1]:
                QMessageBox.warning(self, "Invalid Segments", "Trim segments cannot overlap.")
                return

        self._trimmed_data = trimNXdataToAxisSegments(self.nxdata, self.current_axis_index, segments)
        self.accept()

    def getTrimmedData(self) -> NXdata:
        return self._trimmed_data if self._trimmed_data is not None else self.nxdata
