# AP 2026
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import QuadMesh
from matplotlib.lines import Line2D
import numpy as np
from scipy.ndimage import map_coordinates

from CGTProject.widgets.customPlotToolbar import CustomPlotToolbar
from CGTProject.utilities.lineCutModeEnum import LineCutModeEnum
from CGTProject.utilities.quadmeshData import extract_quadmesh_data
from CGTProject.utilities.NXDataHandler import extractNDArrayFromNXdata, nxlabel
from nexusformat.nexus import NXdata

class PlottedGraphWidget(QWidget):
    lineCutModeActivated = pyqtSignal(bool)  # Emits True if line cut mode is activated, False otherwise
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.quadmesh = None
        self.colorbar = None  # Track colorbar
        
        self.mouse_dragging = False
        
        # Line elements (initially None)
        self.mouse_point : tuple[float, float] = None # (x0, y0)
        self.lineRef : list[Line2D] = None # Line object holds the data to draw line
        
        self.initUI()
        
        # Mouse event connections
        self.cid_press = self.canvas_main.mpl_connect('button_press_event', self.on_press)
        self.cid_motion = self.canvas_main.mpl_connect('motion_notify_event', self.on_motion)
        self.cid_release = self.canvas_main.mpl_connect('button_release_event', self.on_release)
        
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # Create two figures: main plot and line profile
        self.fig_main = Figure(figsize=(8, 6))
        self.canvas_main = FigureCanvas(self.fig_main)
        self.ax_main = self.fig_main.add_subplot(111)
        
        self.fig_profile = Figure(figsize=(8, 3))
        self.canvas_profile = FigureCanvas(self.fig_profile)
        self.ax_profile = self.fig_profile.add_subplot(111)
        
        self.customToolbar = CustomPlotToolbar(self.canvas_main, self)
        
        # self.figure.patch.set_facecolor('white')
        # self.figure.patch.set_alpha(0)
        # #sest tight layout
        # #self.figure.tight_layout()
        # self.canvas.setStyleSheet("background-color:transparent;")
        # # self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout.addWidget(self.customToolbar)
        layout.addWidget(self.canvas_main)
        # layout.addWidget(self.canvas_profile)
        self.setLayout(layout)
        
    
    def updateQuadMeshPlot(self, dataQuadMesh : QuadMesh):
        if dataQuadMesh is not None:
            X, Y, Z = extract_quadmesh_data(dataQuadMesh)
            # Remove old colorbar if it exists
            if self.colorbar is not None:
                print(self.colorbar)
                self.colorbar.remove()
                self.colorbar = None
            self.quadmesh = self.ax_main.pcolormesh(X, Y, Z, shading='auto')
            self.colorbar = self.fig_main.colorbar(self.quadmesh, ax=self.ax_main)
            self.canvas_main.draw()
            
    def updateNXDataPlot(self, extractedData : NXdata):
        x_data, y_data = extractNDArrayFromNXdata(extractedData)
        print(f"Plotting line cut with x_data: {x_data}, y_data: {y_data}, with lengths x: {len(x_data)}, y: {len(y_data)}")

        self.ax_main.clear()
        self.ax_main.plot(x_data, y_data)
        self.ax_main.set_xlabel(nxlabel(extractedData.nxaxes[0]))
        self.ax_main.set_ylabel(nxlabel(extractedData.nxsignal))
        self.ax_main.set_title(extractedData.nxtitle)
        # self.ax_main.draw()
        self.canvas_main.draw()
        
    def updateXYPlot(self, x_data : np.ndarray, y_data : np.ndarray, xlabel: str = "X", ylabel: str = "Y", title: str = "XY Plot", marker: str = 'o', label: str = None, linestyle: str = None, holdprevious:bool = False):
        if not holdprevious:
            self.ax_main.clear()
        self.ax_main.plot(x_data, y_data, marker=marker, label=label, linestyle=linestyle)
        self.ax_main.set_xlabel(xlabel)
        self.ax_main.set_ylabel(ylabel)
        self.ax_main.set_title(title)
        self.ax_main.legend()
        self.canvas_main.draw()
            
    def on_press(self, event):
        """Check if clicking near a line endpoint"""
        if event.inaxes != self.ax_main:
            return
        
        # if not self.lineCutMode: #neither activated
        #     return
        if not self.on_press_line_mode_check(event): #not enabled so dont calculate
            return
        
        self.mouse_point = (event.xdata, event.ydata)
        self.mouse_dragging = True
        self.on_press_line_mode(event)
        
    def on_press_line_mode(self, event):
        pass
        
    def on_press_line_mode_check(self, event):
        return False
    
    def on_motion(self, event):
        """Drag the selected endpoint"""
        #either create line or update line
        if not self.mouse_dragging: #not enabled so dont calculate
            return
        
        if self.mouse_point is None or event.inaxes != self.ax_main: #first point not saved or not in axes
            return
        
        self.mouse_point = (event.xdata, event.ydata)
        self.on_motion_line_mode(event)
        
    def on_motion_line_mode(self, event):
        pass
            
    def on_release(self, event):
        """Stop dragging"""
        # self.mouse_point = None
        self.mouse_dragging = False
        # self.extract_line_cut()  # Auto-update profile
        self.on_release_line_mode(event)
    
    def on_release_line_mode(self, event):
        pass
        
    def getMousePoint(self) -> tuple[float, float]:
        """Get current mouse point (x, y)"""
        return self.mouse_point
    
    def getCenterOfPlot(self) -> tuple[float, float]:
        """Get center coordinates (x_center, y_center) of the axis plot."""
        return self.ax_main.get_xlim()[0] + (self.ax_main.get_xlim()[1] - self.ax_main.get_xlim()[0]) / 2, \
               self.ax_main.get_ylim()[0] + (self.ax_main.get_ylim()[1] - self.ax_main.get_ylim()[0]) / 2
    
    def getDimensions(self) -> tuple[float, float, float, float, float, float, float, float]:
        """Get spatial span (height, width) from quadmesh coords, centered around (0, 0)."""
        if self.quadmesh is not None:
            coords = self.quadmesh.get_coordinates()
            x_vals = coords[:, :, 0]
            y_vals = coords[:, :, 1]

            # Calculate width and height
            width = float(x_vals.max() - x_vals.min())
            height = float(y_vals.max() - y_vals.min())

            # Adjust ranges to center around (0, 0)
            print(f"xval maxes: {x_vals.max()}, mins: {x_vals.min()}, yval maxes: {y_vals.max()}, mins: {y_vals.min()}")
            x_center = (x_vals.max() + x_vals.min()) / 2
            y_center = (y_vals.max() + y_vals.min()) / 2

            print(f"dimensions: {(height, width)}, centered at ({x_center}, {y_center})")
            return height, width, x_center, y_center, x_vals.max(), x_vals.min(), y_vals.max(), y_vals.min()
        return 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    
    def changeColorMap(self, new_cmap: str):
        """Change the colormap of the current plot

        Args:
            new_cmap (str): Name of the new colormap to apply
        """
        if self.quadmesh is not None:
            self.quadmesh.set_cmap(new_cmap)
            self.canvas_main.draw_idle()
            
    def remove_line(self):
        """Remove line and points from plot"""
        if self.lineRef:
            for line in self.lineRef:
                line.remove()
            self.lineRef = None
        
        # Clear profile
        self.ax_profile.clear()
        self.ax_profile.set_title('Line Profile (disabled)')
        self.canvas_profile.draw()
      
