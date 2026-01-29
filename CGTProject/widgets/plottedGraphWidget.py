# AP 2026
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import QuadMesh
from matplotlib.lines import Line2D
import numpy as np
from scipy.ndimage import map_coordinates

from CGTProject.widgets.customPlotToolbar import CustomPlotToolbar

class PlottedGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.quadmesh = None
        self.colorbar = None  # Track colorbar
        
        self.mouse_dragging_point = None
        self.mouse_point1 = None
        self.mouse_point2 = None
        
        # Line elements (initially None)
        self.line_points : list[tuple[float, float]] = [None, None] # [(x0, y0), (x1, y1)]
        self.line : Line2D = None # Line object holds the data to draw line
        
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
        
        self.initLineCutTool()
        self.initLineSegmentCutTool()
        
        layout.addWidget(self.customToolbar)
        layout.addWidget(self.canvas_main)
        # layout.addWidget(self.canvas_profile)
        self.setLayout(layout)
        
    def initLineCutTool(self):
        """Initialize line cut tool components"""
        self.customToolbar.add_lincut_button()
        self.customToolbar.lineCutModeToggled.connect(self.toggleLineCutMode)
        self.line_cut_enabled = False
        self.seg_line_cut_enabled = False
        
    def initLineSegmentCutTool(self):
        """Initialize line segment cut tool components"""
        self.customToolbar.add_seg_lincut_button()
        self.customToolbar.segLineCutModeToggled.connect(self.toggleSegLineCutMode) 
        self.line_cut_enabled = False
        self.seg_line_cut_enabled = False
        
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
            
    def toggleLineCutMode(self, enabled: bool):
        """Enable or disable line cut mode"""
        if enabled and self.seg_line_cut_enabled:
            # self.toggleSegLineCutMode(False)
            self.customToolbar.toggle_seg_line_cut_mode(False)
        if enabled:
            print("Line Cut Mode Enabled")
            self.line_cut_enabled = True
        else:
            print("Line Cut Mode Disabled")
            self.line_cut_enabled = False
            self.remove_line()
            
    def toggleSegLineCutMode(self, enabled: bool):
        """Enable or disable segmented line cut mode"""
        if enabled and self.line_cut_enabled:
            self.customToolbar.toggle_line_cut_mode(False)
        if enabled:
            print("Segmented Line Cut Mode Enabled")
            self.seg_line_cut_enabled = True
        else:
            print("Segmented Line Cut Mode Disabled")
            self.seg_line_cut_enabled = False
            self.remove_line()
            
    def on_press(self, event):
        """Check if clicking near a line endpoint"""
        if event.inaxes != self.ax_main:
            return
        
        if not self.line_cut_enabled and not self.seg_line_cut_enabled: #neither activated
            return
        
        print(f"clicked with: line points: {self.line_points} and line: {self.line}")
        if self.line_points[0] is None and self.line is None: #no line created yet and no first point selected
            self.line_points[0] = (event.xdata, event.ydata)
            return
        # else: # Check distance to endpoints
        elif self.line is not None: #else line already present, check if in range of endpoints to drag; else start new first point
            if self.line_points[0] is None or self.line_points[1] is None: #line created but new click for new line
                self.line_points[0] = (event.xdata, event.ydata)
                return
            x0, y0 = self.line_points[0]
            x1, y1 = self.line_points[1]
            
            dist0 = np.sqrt((event.xdata - x0)**2 + (event.ydata - y0)**2)
            dist1 = np.sqrt((event.xdata - x1)**2 + (event.ydata - y1)**2)
            
            
            if dist0 < 10:  # Within 10 pixels of point 0
                print(f"Clicked near point 0 at ({x0}, {y0})")
                self.mouse_dragging_point = 0
            elif dist1 < 10:  # Within 10 pixels of point 1
                print(f"Clicked near point 1 at ({x1}, {y1})")
                self.mouse_dragging_point = 1
            else: #not within so create new set
                self.line_points[0] = (event.xdata, event.ydata)
    
    def on_motion(self, event):
        """Drag the selected endpoint"""
        #either create line or update line
        print(f"Mouse motion at ({event.xdata}, {event.ydata}) with line points: {self.line_points}, and mouse_dragging points: {self.mouse_dragging_point}")
        if not self.line_cut_enabled and not self.seg_line_cut_enabled: #not enabled so dont calculate
            return
        
        if self.line_points[0] is None or event.inaxes != self.ax_main: #first point not saved or not in axes
            return
        
        
        if self.mouse_dragging_point is None: #not dragging
            if self.line_points[0] is not None and self.line_points[1] is None: #line hasnt been created
                print("create new line")
                self.line_points[1] = (event.xdata, event.ydata)
                self.create_line()
            elif self.line_points[0] is not None and self.line_points[1] is not None: #update second point position
                print("update existing line")
                self.line_points[1] = (event.xdata, event.ydata)
                self.update_line_display()
            return 
        else: #update dragged point
            # Update point position
            print("update point position")
            self.line_points[self.mouse_dragging_point] = (event.xdata, event.ydata)
            
            # Update line and points
            x0, y0 = self.line_points[0]
            x1, y1 = self.line_points[1]
            
            self.mouse_point1.set_data([x0], [y0])
            self.mouse_point2.set_data([x1], [y1])
            
            self.update_line_display()
                
            self.canvas_main.draw_idle()
    
    def on_release(self, event):
        """Stop dragging"""
        self.mouse_dragging_point = None
        self.line_points = [None, None]
        # self.extract_line_cut()  # Auto-update profile
        
    def extract_data_on_line_cut(self):
        """Extract data along the line"""
        if not self.line_cut_enabled:
            return
        
        x0, y0 = self.line_points[0]
        x1, y1 = self.line_points[1]
        
        # If extend_line is enabled, use extended coordinates
        if self.line_cut_enabled:
            extended_points = self.calculate_extended_line(x0, y0, x1, y1)
            x0, y0 = extended_points[0]
            x1, y1 = extended_points[1]
        
        # Number of points along line
        length = int(np.sqrt((x1 - x0)**2 + (y1 - y0)**2))
        num_points = max(length, 100)
        
        # Coordinates along line
        x = np.linspace(x0, x1, num_points)
        y = np.linspace(y0, y1, num_points)
        
        # Extract values (clip to valid range)
        h, w, x_center, y_center, x_max, x_min, y_max, y_min = self.getDimensions()
        coords = np.vstack((
            np.clip(x + x_center, x_min, x_max - 1),
            np.clip(y + y_center, y_min, y_max - 1)
        )).T
        
        # Distance along line
        distance = np.linspace(0, length, num_points)
        
        return distance, coords

    def create_line(self):
        """Create initial line"""
        print(f"Creating line with seg: {self.seg_line_cut_enabled}, line: {self.line_cut_enabled} with line points: {self.line_points}")
        if self.line is not None and self.line_points is not None:
            return  # Line already exists
        # h, w = self.getDimensions()
        x0, y0 = self.line_points[0]
        x1, y1 = self.line_points[1]
        
        if self.seg_line_cut_enabled:
            print("Creating segmented line")
            self.line, = self.ax_main.plot([x0, x1], [y0, y1], 'y-', linewidth=1, alpha=0.5)
            self.mouse_point1, = self.ax_main.plot(x0, y0, 'yo', markersize=4)
            self.mouse_point2, = self.ax_main.plot(x1, y1, 'yo', markersize=4)
        elif self.line_cut_enabled:
            print("Creating extended line")
            self.line_points = self.calculate_extended_line(x0, y0, x1, y1)
            ext_x0, ext_y0, ext_x1, ext_y1 = self.line_points
            self.line, = self.ax_main.plot([ext_x0, ext_x1], [ext_y0, ext_y1], 'y-', linewidth=1, alpha=0.5)
            
        self.canvas_main.draw_idle()
    
    def remove_line(self):
        """Remove line and points from plot"""
        if self.line:
            self.line.remove()
            self.line = None
        if self.mouse_point1:
            self.mouse_point1.remove()
            self.mouse_point1 = None
        if self.mouse_point2:
            self.mouse_point2.remove()
            self.mouse_point2 = None
        
        # Clear profile
        self.ax_profile.clear()
        self.ax_profile.set_title('Line Profile (disabled)')
        self.canvas_profile.draw()
    
    def update_line_display(self):
        """Update line display based on extend_line setting"""
        print("Update Line Display")
        # if not self.line_cut_enabled:
        #     return
        
        x0, y0 = self.line_points[0]
        x1, y1 = self.line_points[1]
        
        
        if self.line_cut_enabled:
            print(f"Updating extended line display with ({x0}, {y0}) to ({x1}, {y1})")
            # Calculate extended line to image boundaries
            extended_points = self.calculate_extended_line(x0, y0, x1, y1)
            ext_x0, ext_y0 = extended_points[0]
            ext_x1, ext_y1 = extended_points[1]
            
            # Remove old extended line if exists
            if self.line:
                self.line.remove()
                self.line = None
                
            # Draw extended line (dashed)
            self.line, = self.ax_main.plot(
                [ext_x0, ext_x1], [ext_y0, ext_y1], 
                'y-', linewidth=1, alpha=0.5
            )
            
            # # Update main line to show selected segment
            # self.line.set_data([x0, x1], [y0, y1])
        elif self.seg_line_cut_enabled:
            print(f"Updating segmented line display with ({x0}, {y0}) to ({x1}, {y1})")
            # Just show segment
            self.line.set_data([x0, x1], [y0, y1])
            #update points
            self.mouse_point1.set_data([x0], [y0])
            self.mouse_point2.set_data([x1], [y1])
        
        self.canvas_main.draw_idle()
    
    def calculate_extended_line(self, x0, y0, x1, y1) -> list[tuple[float, float]]:
        """Calculate line extension to image boundaries"""
        h, w, x_center, y_center, x_max, x_min, y_max, y_min = self.getDimensions()
        
        
        
        # Line equation: y = mx + b
        if abs(x1 - x0) < 1e-6:  # Vertical line
            return [(x0, 0), (x0, h)]
        
        m = (y1 - y0) / (x1 - x0)
        b = y0 - m * x0
        
        # Find intersections with image boundaries
        intersections = []
        
        # Left edge (x=0)
        y_left = m * x_min + b
        if y_min <= y_left <= y_max:
            intersections.append((x_min, y_left))
            
        # Right edge (x=w)
        y_right = m * x_max + b
        if y_min <= y_right <= y_max:
            intersections.append((x_max, y_right))
            
        # Bottom edge (y=0)
        x_bottom = (y_min - b) / m
        if x_min <= x_bottom <= x_max:
            intersections.append((x_bottom, y_min))
            
        # Top edge (y=h)
        x_top = (y_max - b) / m
        if x_min <= x_top <= x_max:
            intersections.append((x_top, y_max))
            
        if len(intersections) >= 2:
            return intersections[:2]
        else:
        
            return [(x0, y0), (x1, y1)]  # Fallback
    
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
