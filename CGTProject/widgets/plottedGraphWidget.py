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

class PlottedGraphWidget(QWidget):
    lineCutModeActivated = pyqtSignal(bool)  # Emits True if line cut mode is activated, False otherwise
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.quadmesh = None
        self.colorbar = None  # Track colorbar
        
        self.mouse_dragging = False
        self.lineCutMode : LineCutModeEnum = None
        
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
        
        self.initVerticleLineCutTool()
        self.initHorizontalLineCutTool()
        self.initVerticleHorizontalLineCutTool()
        
        layout.addWidget(self.customToolbar)
        layout.addWidget(self.canvas_main)
        # layout.addWidget(self.canvas_profile)
        self.setLayout(layout)
        
    def initVerticleLineCutTool(self):
        """Initialize line cut tool components"""
        self.customToolbar.add_vert_lincut_button()
        self.customToolbar.vertLineCutModeToggled.connect(self.toggleVerticleLineCutMode)
        # self.verticle_line_cut_enabled = False
        
    def initHorizontalLineCutTool(self):
        """Initialize line segment cut tool components"""
        self.customToolbar.add_horiz_lincut_button()
        self.customToolbar.horizLineCutModeToggled.connect(self.toggleHorizontalLineCutMode)
        # self.horizontal_line_cut_enabled = False
        
    def initVerticleHorizontalLineCutTool(self):
        """Initialize vertical & horizontal line cut tool components"""
        self.customToolbar.add_vert_horiz_lincut_button()
        self.customToolbar.vertHorizLineCutModeToggled.connect(self.toggleVerticleHorizontalLineCutMode) 
        # self.verticle_horizontal_line_cut_enabled = False
        
    def plotQuadMeshData(self, dataQuadMesh : QuadMesh):
        # self.canvas.draw()
        if dataQuadMesh is not None:
            
            # Remove old colorbar if it exists
            if self.colorbar is not None:
                print(self.colorbar)
                self.colorbar.remove()
                self.colorbar = None
                
            self.ax_main.clear()
            # self.figure.clear()
            
            X, Y, Z = self.extract_quadmesh_data(dataQuadMesh)
            self.quadmesh = self.ax_main.pcolormesh(X, Y, Z, shading='auto')
            
            # Store reference to new colorbar
            self.colorbar = self.fig_main.colorbar(self.quadmesh, ax=self.ax_main)
            
            self.canvas_main.draw()
            
    # Extract data from existing QuadMesh
    def extract_quadmesh_data(self, quadmesh : QuadMesh):
        """Get X, Y, Z arrays from QuadMesh object"""
        # Get the array data
        array = quadmesh.get_array()
        coords = quadmesh.get_coordinates()
        
        # Coordinates define cell corners, data is cell centers
        M, N = coords.shape[:2]
        Z = array.reshape(M-1, N-1)  # Data is one smaller in each dimension
        
        X = coords[:, :, 0]
        Y = coords[:, :, 1]
        return X, Y, Z
    
    def updateQuadMeshPlot(self, dataQuadMesh : QuadMesh):
        if dataQuadMesh is not None:
            X, Y, Z = self.extract_quadmesh_data(dataQuadMesh)
            # Remove old colorbar if it exists
            if self.colorbar is not None:
                print(self.colorbar)
                self.colorbar.remove()
                self.colorbar = None
            self.quadmesh = self.ax_main.pcolormesh(X, Y, Z, shading='auto')
            self.colorbar = self.fig_main.colorbar(self.quadmesh, ax=self.ax_main)
            self.canvas_main.draw()
            
    def toggleVerticleLineCutMode(self, enabled: bool):
        """Enable or disable line cut mode"""
        # if enabled and (self.horizontal_line_cut_enabled or self.verticle_horizontal_line_cut_enabled):
        if enabled and self.lineCutMode != LineCutModeEnum.VERTICAL:
            self.customToolbar.toggle_horizontal_line_cut_mode(False)
            self.customToolbar.toggle_vert_horiz_line_cut_mode(False)
        if enabled:
            print("Line Cut Mode Enabled")
            # self.verticle_line_cut_enabled = True
            self.lineCutMode = LineCutModeEnum.VERTICAL
            #create initial line in center of plot
            self.mouse_point = self.getCenterOfPlot()
            self.update_line_display()
            self.lineCutModeActivated.emit(True)
        else:
            print("Line Cut Mode Disabled")
            # self.verticle_line_cut_enabled = False
            self.lineCutMode = None
            self.remove_line()
            self.lineCutModeActivated.emit(False)
            
    def toggleHorizontalLineCutMode(self, enabled: bool):
        """Enable or disable segmented line cut mode"""
        # if enabled and (self.verticle_line_cut_enabled or self.verticle_horizontal_line_cut_enabled):
        if enabled and self.lineCutMode != LineCutModeEnum.HORIZONTAL:
            self.customToolbar.toggle_verticle_line_cut_mode(False)
            self.customToolbar.toggle_vert_horiz_line_cut_mode(False)
        if enabled:
            print("Segmented Line Cut Mode Enabled")
            # self.horizontal_line_cut_enabled = True
            self.lineCutMode = LineCutModeEnum.HORIZONTAL
            #create initial line in center of plot
            self.mouse_point = self.getCenterOfPlot()
            self.update_line_display()
            self.lineCutModeActivated.emit(True)
        else:
            print("Segmented Line Cut Mode Disabled")
            # self.horizontal_line_cut_enabled = False
            self.lineCutMode = None
            self.remove_line()
            self.lineCutModeActivated.emit(False)
            
    def toggleVerticleHorizontalLineCutMode(self, enabled: bool):
        """Enable or disable vertical & horizontal line cut mode"""
        # if enabled and (self.verticle_line_cut_enabled or self.horizontal_line_cut_enabled):
        if enabled and self.lineCutMode != LineCutModeEnum.BOTH:
            self.customToolbar.toggle_verticle_line_cut_mode(False)
            self.customToolbar.toggle_horizontal_line_cut_mode(False)
        if enabled:
            print("Vert & Horiz Line Cut Mode Enabled")
            # self.verticle_horizontal_line_cut_enabled = True
            self.lineCutMode = LineCutModeEnum.BOTH
            #create initial line in center of plot
            self.mouse_point = self.getCenterOfPlot()
            self.update_line_display()
            self.lineCutModeActivated.emit(True)
        else:
            print("Vert & Horiz Line Cut Mode Disabled")
            # self.verticle_horizontal_line_cut_enabled = False
            self.lineCutMode = None
            self.remove_line()
            
    def on_press(self, event):
        """Check if clicking near a line endpoint"""
        if event.inaxes != self.ax_main:
            return
        
        if not self.lineCutMode: #neither activated
            return
        
        self.mouse_point = (event.xdata, event.ydata)
        self.mouse_dragging = True
    
    def on_motion(self, event):
        """Drag the selected endpoint"""
        #either create line or update line
        if not self.mouse_dragging: #not enabled so dont calculate
            return
        
        if self.mouse_point is None or event.inaxes != self.ax_main: #first point not saved or not in axes
            return
        
        self.mouse_point = (event.xdata, event.ydata)
        
        if self.lineCutMode == LineCutModeEnum.BOTH:
            print("vert horiz line cut mode")
            #will plot a cross line
            self.update_line_display()
        
        if self.lineCutMode == LineCutModeEnum.VERTICAL:
            print("vert line cut mode")
            self.update_line_display()
            
        if self.lineCutMode == LineCutModeEnum.HORIZONTAL:
            print("horiz line cut mode")
            self.update_line_display()
            
    def on_release(self, event):
        """Stop dragging"""
        # self.mouse_point = None
        self.mouse_dragging = False
        # self.extract_line_cut()  # Auto-update profile
        
    def update_line_display(self):
        """Update line position on plot"""
        if not self.lineRef:
            #create empty Line2D object
            self.lineRef = [Line2D([], [], color='red')]
            self.ax_main.add_line(self.lineRef[0])
        
        x0, y0 = self.mouse_point
        
        print(f"Updating line display at point: ({x0}, {y0})")
        
        if self.lineCutMode == LineCutModeEnum.VERTICAL:
            x_vals = [x0, x0]
            y_vals = [self.ax_main.get_ylim()[0], self.ax_main.get_ylim()[1]]
            
        elif self.lineCutMode == LineCutModeEnum.HORIZONTAL:
            x_vals = [self.ax_main.get_xlim()[0], self.ax_main.get_xlim()[1]]
            y_vals = [y0, y0]
            
        elif self.lineCutMode == LineCutModeEnum.BOTH:  # BOTH
            # vert line
            x_vals_vert = [x0, x0]
            y_vals_vert = [self.ax_main.get_ylim()[0], self.ax_main.get_ylim()[1]]
            self.lineRef[0].set_data(x_vals_vert, y_vals_vert)
            # horiz line
            x_vals_horiz = [self.ax_main.get_xlim()[0], self.ax_main.get_xlim()[1]]
            y_vals_horiz = [y0, y0]
            if len(self.lineRef) < 2:
                self.lineRef.append(Line2D([], [], color='red'))
                self.ax_main.add_line(self.lineRef[1])
            self.lineRef[1].set_data(x_vals_horiz, y_vals_horiz)
            self.canvas_main.draw_idle()
            return
        
        self.lineRef[0].set_data(x_vals, y_vals)
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

    def getLineCutMode(self) -> LineCutModeEnum:
        return self.lineCutMode
    
    def changeColorMap(self, new_cmap: str):
        """Change the colormap of the current plot

        Args:
            new_cmap (str): Name of the new colormap to apply
        """
        if self.quadmesh is not None:
            self.quadmesh.set_cmap(new_cmap)
            self.canvas_main.draw_idle()
      
