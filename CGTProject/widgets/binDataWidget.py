# AP 2026

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QSpinBox,
    QFormLayout,
)
from PyQt5.QtCore import pyqtSignal

import numpy as np

from CGTProject.utilities.NXDataHandler import binNXdataByFactors


class BinDataWidget(QWidget):
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

        self._factor_spinboxes: list[QSpinBox] = []
        self._axis_names: list[str] = []

    def _applyBinFactors(self):
        print("applying bin factors")
        self.notifyInfo.emit("Starting bin operation")
        try:
            self.progressChanged.emit(0, "Binning data")
            base_data = self.dataModel.getCurrentData()
            if base_data is None:
                return
            if not self._factor_spinboxes:
                return

            factors = [sb.value() for sb in self._factor_spinboxes]
            if all(f <= 1 for f in factors):
                self.notifyWarning.emit("All bin factors are 1; nothing to do.")
                return

            reduction = self.reductionCombo.currentText()

            self.progressChanged.emit(25, "Reducing signal")
            binned_data = binNXdataByFactors(base_data, factors, reduction=reduction)
            self.progressChanged.emit(75, "Applying binned data")
            self.dataModel.replaceCurrentData(binned_data) #TODO only implemented on temperature data model, need to implement on other data models

            self.progressChanged.emit(85, "Updating display")
            slice_axis_index = self.dataModel.getSliceAxisIndex()
            max_depth = len(np.asarray(self.dataModel.getCurrentData().nxaxes[slice_axis_index])) - 1
            max_depth = max(0, max_depth)
            self.plotSliderWidget.setMaximum(max_depth)
            if self.plotSliderWidget.value() > max_depth:
                self.plotSliderWidget.setValue(max_depth)

            print("finished applying bin factors")
            self.notifySuccess.emit("Finished applying bin factors")

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

    def _buildBinAdditionalOptions(self) -> QWidget:
        base_data = self.dataModel.getCurrentData()
        bin_root = QWidget()
        bin_layout = QVBoxLayout(bin_root)

        bin_layout.addWidget(QLabel("Bin current dataset by integer factor per axis."))

        if base_data is not None:
            axes_attr = base_data.attrs['axes']
            self._axis_names = [axes_attr] if isinstance(axes_attr, str) else list(axes_attr)
            signal_shape = np.asarray(base_data[base_data.attrs['signal']]).shape
        else:
            self._axis_names = []
            signal_shape = ()

        factor_form = QFormLayout()
        self._factor_spinboxes = []
        for axis_idx, axis_name in enumerate(self._axis_names):
            dim_size = signal_shape[axis_idx] if axis_idx < len(signal_shape) else 1
            spinbox = QSpinBox()
            spinbox.setMinimum(1)
            spinbox.setMaximum(max(1, int(dim_size)))
            spinbox.setValue(1)
            factor_form.addRow(QLabel(f"{axis_name} factor:"), spinbox)
            self._factor_spinboxes.append(spinbox)
        bin_layout.addLayout(factor_form)

        reduction_row = QHBoxLayout()
        reduction_row.addWidget(QLabel("Reduction:"))
        self.reductionCombo = QComboBox()
        self.reductionCombo.addItems(["mean", "sum"])
        reduction_row.addWidget(self.reductionCombo)
        reduction_row.addStretch(1)
        bin_layout.addLayout(reduction_row)

        button_row = QHBoxLayout()
        apply_btn = QPushButton("Submit Bin")
        apply_btn.clicked.connect(self._applyBinFactors)
        return_btn = QPushButton("Return To Full Dataset")
        return_btn.clicked.connect(self._returnToFullDataset)
        button_row.addWidget(apply_btn)
        button_row.addWidget(return_btn)
        button_row.addStretch(1)
        bin_layout.addLayout(button_row)

        return bin_root
