#AP 2026

from CGTProject.widgets.plottedGraphWidget import PlottedGraphWidget
from CGTProject.utilities.lineCutModeEnum import LineCutModeEnum
from matplotlib.lines import Line2D

class PlottedLineCutGraphWidget(PlottedGraphWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineCutMode : LineCutModeEnum = None
        
        self.moveLine : int = None # 0 or 1 for the verticle line index (since we have two verticle lines in the verticleLineCutMode)
        
        print(f"verticle line cut tool initialize in PlottedLineCutGraphWidget")
        self.initVerticleLineCutTool()
        
    def initVerticleLineCutTool(self):
        """Initialize line cut tool components"""
        self.customToolbar.add_vert_lincut_button()
        self.customToolbar.vertLineCutModeToggled.connect(self.toggleVerticleLineCutMode)
        # self.verticle_line_cut_enabled = False
        
    def toggleVerticleLineCutMode(self, enabled: bool):
        """Enable or disable line cut mode"""
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
            
    def on_press_line_mode_check(self, event):
        return self.lineCutMode
    
    def on_press_line_mode(self, event):
        #see which line the mouse press was closest to
        if self.lineCutMode == LineCutModeEnum.VERTICAL and self.lineRef is not None:
            x0, y0 = self.mouse_point
            line_1 = self.lineRef[0].get_xdata()[0] #xdata is the same for both points since vertical line
            line_2 = self.lineRef[1].get_xdata()[0]
            if abs(x0 - line_1) < 0.1: #if mouse is close enough to the line, allow dragging
                self.moveLine = 0
            elif abs(x0 - line_2) < 0.1:
                self.moveLine = 1
            else:
                self.moveLine = None
        else:
            self.moveLine = None
            
    def on_release_line_mode(self, event):
        self.moveLine = None
    
    def on_motion_line_mode(self, event):
        if self.lineCutMode == LineCutModeEnum.VERTICAL:
            # print("vert line cut mode")
            self.update_line_display()
            
    def update_line_display(self):
        """Update the line display based on the current mouse point"""
        if self.mouse_point is not None and self.lineCutMode == LineCutModeEnum.VERTICAL:
            x0, y0 = self.mouse_point
            # Get current y-limits of the plot to draw a vertical line across the entire height
            y_min, y_max = self.ax_main.get_ylim()
            x_min, x_max = self.ax_main.get_xlim()
            if self.lineRef is None:
                # Create line 1 slightly offset from center and line 2 slightly offset in the other direction
                x_offset = (x_max - x_min) * 0.1  # 10% offset
                x1 = x0 - x_offset if x0 > (x_min + x_offset) else x0 + x_offset
                self.lineRef = [
                    Line2D([x0, x0], [y_min, y_max], color='red', linestyle='--'),
                    Line2D([x1, x1], [y_min, y_max], color='red', linestyle='--')
                ]
                self.ax_main.add_line(self.lineRef[0])
                self.ax_main.add_line(self.lineRef[1])
            else:
                # Update existing line positions
                if self.moveLine is not None:
                    if self.moveLine == 0:
                        self.lineRef[0].set_xdata([x0, x0])
                        self.lineRef[0].set_ydata([y_min, y_max])
                    elif self.moveLine == 1:
                        self.lineRef[1].set_xdata([x0, x0])
                        self.lineRef[1].set_ydata([y_min, y_max])
                else:
                    pass
            self.canvas_main.draw_idle()
            
    def getLineCutMode(self) -> LineCutModeEnum:
        return self.lineCutMode
    
    def getTwoVertLines(self) -> tuple[float, float]:
        """Get the x positions of the two vertical lines as a tuple (line1_x, line2_x)"""
        if self.lineRef is not None and len(self.lineRef) >= 2:
            line1_x = self.lineRef[0].get_xdata()[0]  # xdata is the same for both points since vertical line
            line2_x = self.lineRef[1].get_xdata()[0]
            return line1_x, line2_x
        return None