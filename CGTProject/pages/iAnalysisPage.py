# AP 2026
import os

from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QDialog, QVBoxLayout, QFileDialog, QProgressDialog, QApplication
from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QTimer

from abc import abstractmethod
import numpy as np

from CGTProject.widgets.fileManagerWidget import FileManagerWidget
from CGTProject.models.temperatureDataModel import TemperatureDataModel
from CGTProject.models.dataModel import DataModel
from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget
from CGTProject.widgets.plottedLineModesGraphWidget import PlottedLineModesGraphWidget
from CGTProject.widgets.lineCutOptionsDialogue import LineCutOptionsDialogue
from CGTProject.widgets.colorRampSlider import ColorRampWidget
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

        # Coalesce rapid slider events so we don't re-render on every tick.
        self._pending_plot_slider_value: int | None = None
        self._plot_update_timer = QTimer(self)
        self._plot_update_timer.setSingleShot(True)
        self._plot_update_timer.timeout.connect(self._applyPendingPlotSliderValue)

        # When dragging the slider, avoid expensive autoscale on every frame.
        self._autoscale_next_redraw: bool = True
        
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
        self.plotSliderWidget.sliderReleased.connect(self._onPlotSliderReleased)

        self.plotSliderValueLabel = QLabel("Slice: 0 / 0")
        self.plotSliderValueLabel.setAlignment(Qt.AlignCenter)
        self.plotSliderWidget.valueChanged.connect(self._updatePlotSliderValueLabel)

        self.colorRampWidget = ColorRampWidget()
        self.colorRampWidget.valueChanged.connect(self.onContrastRampValueChanged)

        self.plotControlsLayout = QVBoxLayout()
        self.plotControlsLayout.addWidget(self.plotSliderWidget)
        self.plotControlsLayout.addWidget(self.plotSliderValueLabel)
        self.plotControlsLayout.addWidget(self.colorRampWidget)
        self.layout.addLayout(self.plotControlsLayout, 4, 0, 1, 2)

        self.additionalOptionsCombo = QComboBox()
        self.additionalOptionsCombo.addItems(["--", "Change colormap", "Skew Angle", "Download current data (.nxs)"])
        self.additionalOptionsCombo.setEnabled(True)
        self.additionalOptionsCombo.currentIndexChanged.connect(self.onAdditionalOptionChanged)
        self.layout.addWidget(self.additionalOptionsCombo, 2, 2, 1, 1)

        self.additionalOptionsLayout = QVBoxLayout()
        self.layout.addLayout(self.additionalOptionsLayout, 3, 2, 1, 1)

        self.setLayout(self.layout)
        self._updatePlotSliderValueLabel(self.plotSliderWidget.value())
            
    def redrawPlot(self):
        if self.dataModel:
            quad_mesh_data = self.dataModel.getQuadMeshAtCurrentIndex()
            if quad_mesh_data:
                autoscale = bool(getattr(self, "_autoscale_next_redraw", True))
                self._autoscale_next_redraw = True
                self.plotted_graph_widget.updateQuadMeshPlot(quad_mesh_data, autoscale=autoscale)
                self._applyCurrentContrastRamp()
                self._updateColorRampLabelFromPlot()

    def _updatePlotSliderValueLabel(self, value: int):
        axis_label, axis_value = self._getSliceAxisValue(value)
        if axis_label is None or axis_value is None:
            self.plotSliderValueLabel.setText(f"Slice: {value} / {self.plotSliderWidget.maximum()}")
        else:
            self.plotSliderValueLabel.setText(f"{axis_label}: {axis_value:.6g}")

    def _setPlotSliderMaximum(self, maximum: int):
        self.plotSliderWidget.setMaximum(maximum)
        self._updatePlotSliderValueLabel(self.plotSliderWidget.value())

    def _getActivePlotData(self):
        if self.dataModel is None:
            return None
        return self.dataModel.getCurrentData()

    def _getSliceAxisValue(self, value: int):
        data = self._getActivePlotData()
        if data is None or self.dataModel is None:
            return None, None

        slice_axis_index = self.dataModel.getSliceAxisIndex()
        if slice_axis_index < 0 or slice_axis_index >= len(data.nxaxes):
            return None, None

        axis_field = data.nxaxes[slice_axis_index]
        axis_values = np.asarray(axis_field)
        if axis_values.size == 0:
            return None, None

        clamped_value = max(0, min(int(value), axis_values.size - 1))
        axis_label = getattr(axis_field, "nxname", None) or f"Axis {slice_axis_index}"
        return axis_label, float(axis_values[clamped_value])

    def _updateColorRampLabelFromPlot(self):
        if not hasattr(self, "colorRampWidget") or not self.plotted_graph_widget:
            return

        limits = self.plotted_graph_widget.getCurrentColorLimits()
        if not limits:
            return

        vmin, vmax = limits
        self.colorRampWidget.setContrastLimits(vmin, vmax)

    def onContrastRampValueChanged(self, black_position: float, white_position: float):
        if self.plotted_graph_widget:
            limits = self.plotted_graph_widget.setNormalizedContrast(black_position, white_position)
            if limits is not None:
                self.colorRampWidget.setContrastLimits(*limits)

    def _applyCurrentContrastRamp(self):
        if not self.plotted_graph_widget or not hasattr(self, "colorRampWidget"):
            return
        black_position, white_position = self.colorRampWidget.get_slider_position()
        limits = self.plotted_graph_widget.setNormalizedContrast(black_position, white_position)
        if limits is not None:
            self.colorRampWidget.setContrastLimits(*limits)
      
    def onPlotSliderValueChanged(self, value):
        # Debounce rapid slider movement; keep UI responsive.
        self._pending_plot_slider_value = int(value)
        self._autoscale_next_redraw = False
        # Restart timer to coalesce events during dragging.
        self._plot_update_timer.start(100)

    def _onPlotSliderReleased(self):
        # Force a final redraw with autoscale once the user lets go.
        self._autoscale_next_redraw = True
        self._applyPendingPlotSliderValue()

    def _applyPendingPlotSliderValue(self):
        if self._pending_plot_slider_value is None or not self.dataModel:
            return
        value = self._pending_plot_slider_value
        self._pending_plot_slider_value = None
        self.dataModel.setIndex(value)
        self.redrawPlot()
            
    def onAdditionalOptionChanged(self, index):
        selected_option = self.additionalOptionsCombo.itemText(index) if index >= 0 else self.additionalOptionsCombo.currentText()
        print("test")
        print(selected_option == "Download current data (.nxs)")
        print(f"Additional option selected: {selected_option}")
        if selected_option == "--":
            self._clearAdditionalOptionsLayout()
        elif selected_option == "Change colormap":
            changeColormap = QComboBox()
            changeColormap.addItems(["viridis", "plasma", "inferno", "magma", "cividis"])
            changeColormap.currentIndexChanged.connect(lambda newCmap: self.changeColormap(changeColormap.currentText()))
            self._clearAdditionalOptionsLayout()
            self.additionalOptionsLayout.addWidget(changeColormap)
        elif selected_option == "Skew Angle":
            skewAngleLabel = QLabel("Skew Angle:")
            skewAngleSlider = QSlider(Qt.Horizontal)
            skewAngleSlider.setMinimum(-45)
            skewAngleSlider.setMaximum(45)
            skewAngleSlider.setValue(0)
            skewAngleSlider.setTickPosition(QSlider.TicksBelow)
            skewAngleSlider.setTickInterval(1)
            skewAngleSlider.sliderReleased.connect(lambda: self.applySkewAngle(skewAngleSlider.value()))
            self._clearAdditionalOptionsLayout()
            self.additionalOptionsLayout.addWidget(skewAngleLabel)
            self.additionalOptionsLayout.addWidget(skewAngleSlider)
        elif selected_option == "Download current data (.nxs)":
            QTimer.singleShot(0, self.downloadCurrentDataAsNxs)
            QTimer.singleShot(0, lambda: self.additionalOptionsCombo.setCurrentIndex(0))

    def _clearAdditionalOptionsLayout(self):
        for i in reversed(range(self.additionalOptionsLayout.count())):
            widgetToRemove = self.additionalOptionsLayout.itemAt(i).widget()
            if widgetToRemove is not None:
                self.additionalOptionsLayout.removeWidget(widgetToRemove)
                widgetToRemove.setParent(None)

    def _buildExportPath(self, save_root: str) -> str:
        data_model = getattr(self, "dataModel", None)
        data_path_root = str(getattr(data_model, "dataPathRoot", "") or "")
        sample_type = os.path.basename(os.path.dirname(data_path_root)) if data_path_root else ""
        sample_name = os.path.basename(data_path_root) if data_path_root else ""
        temperature = str(getattr(data_model, "temperature", "") or "current")

        export_folder = save_root
        if sample_type:
            export_folder = os.path.join(export_folder, sample_type)
        if sample_name:
            export_folder = os.path.join(export_folder, sample_name)

        if sample_name:
            # Use _standalone_hkl suffix so the loader recognizes it as standalone without creating a new one
            file_name = f"{sample_name}_{temperature}_standalone_hkl.nxs"
        else:
            file_name = f"current_{temperature}_standalone_hkl.nxs"

        return os.path.join(export_folder, file_name)

    def _writeStandaloneNXdata(self, export_path: str, nxdata: NXdata, progress_dialog: QProgressDialog | None = None):
        import h5py

        os.makedirs(os.path.dirname(os.path.abspath(export_path)) or ".", exist_ok=True)

        def _normalize_name(name):
            if isinstance(name, bytes):
                return name.decode("utf-8", errors="ignore")
            return str(name)

        axes_attr = nxdata.attrs.get("axes", ())
        axis_names = [_normalize_name(axes_attr)] if isinstance(axes_attr, str) else [_normalize_name(name) for name in list(axes_attr)]
        signal_name = nxdata.attrs.get("signal", None)
        if not signal_name:
            signal_name = getattr(getattr(nxdata, "nxsignal", None), "nxname", None) or "data"
        signal_name = _normalize_name(signal_name)

        total_steps = max(1, len(axis_names) + 1)
        step = 0

        with h5py.File(export_path, "w") as nexus_file:
            entry = nexus_file.create_group("entry")
            entry.attrs["NX_class"] = "NXentry"
            entry.attrs["default"] = "transform"

            transform_group = entry.create_group("transform")
            transform_group.attrs["NX_class"] = "NXdata"
            transform_group.attrs["signal"] = signal_name
            if len(axis_names) == 1:
                transform_group.attrs["axes"] = axis_names[0]
            else:
                transform_group.attrs["axes"] = np.array(axis_names, dtype="S")

            if hasattr(nxdata, "nxtitle") and nxdata.nxtitle:
                transform_group.attrs["title"] = nxdata.nxtitle

            # Get signal shape for axis truncation
            signal_data = np.asarray(nxdata[signal_name])
            signal_shape = signal_data.shape

            # Write axis datasets, truncating to match signal dimensions
            for axis_idx, axis_name in enumerate(axis_names):
                if progress_dialog and progress_dialog.wasCanceled():
                    return
                
                axis_raw = np.asarray(nxdata[axis_name])
                # Truncate axis to match signal dimension
                if axis_idx < len(signal_shape):
                    expected_len = signal_shape[axis_idx]
                    if axis_raw.size > expected_len:
                        axis_raw = axis_raw[:expected_len]
                
                axis_dataset = transform_group.create_dataset(axis_name, data=axis_raw)
                for attr_name, attr_value in nxdata[axis_name].attrs.items():
                    axis_dataset.attrs[attr_name] = attr_value

                step += 1
                if progress_dialog:
                    progress = int(step / total_steps * 100)
                    progress_dialog.setLabelText(f"Saving axis: {axis_name}")
                    progress_dialog.setValue(progress)
                    QApplication.processEvents()

            # Write signal dataset
            if progress_dialog and progress_dialog.wasCanceled():
                return
            signal_dataset = transform_group.create_dataset(signal_name, data=np.asarray(nxdata[signal_name]))
            for attr_name, attr_value in nxdata[signal_name].attrs.items():
                signal_dataset.attrs[attr_name] = attr_value

            step += 1
            if progress_dialog:
                progress_dialog.setLabelText(f"Saving signal: {signal_name}")
                progress_dialog.setValue(100)
                QApplication.processEvents()

    def downloadCurrentDataAsNxs(self):
        print("getting current data now")
        current_data = self._getActivePlotData()
        if current_data is None:
            print("No current data available to export.")
            return
        print("Retrieved data, opening file dialog")

        save_root = QFileDialog.getExistingDirectory(
            self,
            "Select folder to save current data",
            self.last_directory or str(self.settings.value("lastDirectory", "") or ""),
            QFileDialog.Option.DontUseNativeDialog,
        )
        if not save_root:
            return

        export_path = self._buildExportPath(save_root)

        progress = QProgressDialog("Saving current data...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setAutoClose(True)
        progress.setValue(0)

        # perform write with progress updates; allow cancellation
        self._writeStandaloneNXdata(export_path, current_data, progress_dialog=progress)
        progress.setValue(100)

        self.last_directory = save_root
        self.settings.setValue("lastDirectory", save_root)
        print(f"Saved current data to: {export_path}")
            
    def applySkewAngle(self, angle):
        print(f"Applying skew angle: {angle}")
        quadmesh = self.dataModel.updateSkewAngle(angle)
        self.plotted_graph_widget.updateQuadMeshPlot(quadmesh)
        self._applyCurrentContrastRamp()
        
    def changeColormap(self, newCmap):
        print("Changing colormap...")
        # Placeholder for colormap change logic
        if self.plotted_graph_widget:
            self.plotted_graph_widget.changeColorMap("new_cmap")
            self.redrawPlot()


