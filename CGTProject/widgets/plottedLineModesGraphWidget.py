# AP 2026

from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget
from CGTProject.utilities.lineCutModeEnum import LineCutModeEnum
from matplotlib.lines import Line2D
from PyQt5.QtCore import pyqtSignal


class PlottedLineModesGraphWidget(PlottedGraphWidget):
    openDeltaPDFOptionsDialogue = pyqtSignal()  # Signal to indicate Gaussian filter state and sigma value
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineCutMode : LineCutModeEnum = None
        
        # self.initVerticleLineCutTool()
        # self.initHorizontalLineCutTool()
        print(f"verticle horizontal line cut tool initialize in PlottedLineModesGraphWidget")
        self.initVerticleHorizontalLineCutTool()
        self.initDeltaPDFTool()
        
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
        
    def initDeltaPDFTool(self):
        self.customToolbar.add_deltaPDF_button()
        self.customToolbar.deltaPDFToggled.connect(self.toggleDeltaPDFMode)
        
    def toggleDeltaPDFMode(self, enabled: bool):
        #open Dialogue
        if enabled:
            self.openDeltaPDFOptionsDialogue.emit()
        else:
            self.customToolbar.toggle_deltaPDF_mode(False)
            
        
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
        print(f"Line cut mode: {self.lineCutMode}")
        if enabled and (self.lineCutMode == LineCutModeEnum.VERTICAL or self.lineCutMode == LineCutModeEnum.HORIZONTAL):
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
        
    def on_press_line_mode_check(self, event):
        return self.lineCutMode
    
    def on_motion_line_mode(self, event):
        if self.lineCutMode == LineCutModeEnum.BOTH:
            # print("vert horiz line cut mode")
            #will plot a cross line
            self.update_line_display()
        
        if self.lineCutMode == LineCutModeEnum.VERTICAL:
            # print("vert line cut mode")
            self.update_line_display()
            
        if self.lineCutMode == LineCutModeEnum.HORIZONTAL:
            # print("horiz line cut mode")
            self.update_line_display()
            
    def update_line_display(self):
        """Update line position on plot"""
        if not self.lineRef:
            #create empty Line2D object
            self.lineRef = [Line2D([], [], color='red')]
            self.ax_main.add_line(self.lineRef[0])
        
        x0, y0 = self.mouse_point
        
        # print(f"Updating line display at point: ({x0}, {y0})")
        
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
        
    def getLineCutMode(self) -> LineCutModeEnum:
        return self.lineCutMode
            
