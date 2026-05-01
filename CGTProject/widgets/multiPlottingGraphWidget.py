# AP 2026

from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget, CustomPlotToolbar
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QVBoxLayout, QSizePolicy


class MultiPlottingGraphWidget(PlottedGraphWidget):
    """A compact multi-panel plot widget for previewing related 2D slices side by side."""

    def initUI(self):
        layout = QVBoxLayout()

        self.fig_main = Figure(figsize=(10, 4))
        self.canvas_main = FigureCanvas(self.fig_main)
        self.canvas_main.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas_main.updateGeometry()
        self.canvas_main.setMinimumHeight(240)

        self.ax_left = self.fig_main.add_subplot(121)
        self.ax_right = self.fig_main.add_subplot(122)
        self.axes = [self.ax_left, self.ax_right]

        self.fig_main.subplots_adjust(left=0.05, right=0.98, bottom=0.10, top=0.95, wspace=0.28)

        self.fig_profile = Figure(figsize=(8, 3))
        self.canvas_profile = FigureCanvas(self.fig_profile)
        self.canvas_profile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.canvas_profile.updateGeometry()
        self.canvas_profile.setMinimumHeight(100)
        self.ax_profile = self.fig_profile.add_subplot(111)

        self.customToolbar = CustomPlotToolbar(self.canvas_main, self)

        layout.addWidget(self.customToolbar)
        layout.addWidget(self.canvas_main, 1)
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def updateDualPColorMeshPlot(
        self,
        left_data,
        right_data,
        *,
        left_title: str = "Left Plot",
        right_title: str = "Right Plot",
        left_cmap: str = "gray",
        right_cmap: str = "viridis",
        left_aspect: str | float = "auto",
        right_aspect: str | float = "auto",
    ):
        for ax in self.axes:
            ax.clear()

        self.quadmesh = None
        self.colorbar = None

        self.ax_left.pcolormesh(left_data, shading="auto", cmap=left_cmap)
        self.ax_left.set_title(left_title)
        self.ax_left.set_aspect(left_aspect)

        self.ax_right.pcolormesh(right_data, shading="auto", cmap=right_cmap)
        self.ax_right.set_title(right_title)
        self.ax_right.set_aspect(right_aspect)

        self.canvas_main.draw_idle()