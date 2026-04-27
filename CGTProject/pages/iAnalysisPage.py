# AP 2026
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QCheckBox, QDialog, QVBoxLayout
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
        self.additionalOptionsCombo.addItems(["--", "Change colormap", "Skew Angle"])
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
        self._applyCurrentContrastRamp()
        
    def changeColormap(self, newCmap):
        print("Changing colormap...")
        # Placeholder for colormap change logic
        if self.plotted_graph_widget:
            self.plotted_graph_widget.changeColorMap("new_cmap")
            self.redrawPlot()


