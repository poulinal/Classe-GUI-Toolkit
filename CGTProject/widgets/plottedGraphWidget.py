# AP 2026
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QSettings

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import QuadMesh

import numpy as np

class PlottedGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.colorbar = None  # Track colorbar
        
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
    def plotQuadMeshData(self, dataQuadMesh : QuadMesh):
        # self.canvas.draw()
        if dataQuadMesh is not None:
            
            # Remove old colorbar if it exists
            if self.colorbar is not None:
                print(self.colorbar)
                self.colorbar.remove()
                self.colorbar = None
                
            self.ax.clear()
            # self.figure.clear()
            
            X, Y, Z = self.extract_quadmesh_data(dataQuadMesh)
            quadmesh = self.ax.pcolormesh(X, Y, Z, shading='auto')
            
            # Store reference to new colorbar
            self.colorbar = self.figure.colorbar(quadmesh, ax=self.ax)
            
            self.canvas.draw()
            
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