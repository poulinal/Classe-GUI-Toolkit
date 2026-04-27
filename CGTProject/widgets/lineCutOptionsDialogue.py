# AP 2026

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QDialog, QCheckBox, QFormLayout, QPushButton, QSlider, QMessageBox
from PyQt5.QtCore import Qt, QSettings
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import QuadMesh

from nexusformat.nexus import NXdata
from nxs_analysis_tools import Scissors

from CGTProject.utilities.HKLPlaneEnum import HKLPlaneEnum

class LineCutOptionsDialogue(QDialog):
    def __init__(self, currentHKLPlane : HKLPlaneEnum, mousePos : tuple[float, float], currentData : NXdata, dataAxisMinMax : tuple[tuple[float, float], tuple[float, float], tuple[float, float]], dataAxisResolutions : tuple[float, float, float], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Line Cut Options")
        self.setModal(True)
        self.currentData = currentData
        self.mousePos = mousePos
        self.currentHKLPlane = currentHKLPlane
        
        self.initUI(dataAxisMinMax, dataAxisResolutions)
        
    def initUI(self, dataAxisMinMax : tuple[tuple[float, float], tuple[float, float], tuple[float, float]], dataAxisResolutions : tuple[float, float, float]):
        layout = QVBoxLayout()
        
        label = QLabel("Options for Line Cut:")
        label.setAlignment(Qt.AlignCenter)
        
        #choose hmin, hmax, kmin kmax, Lcenter deltaL
        self.hMinLabel = QLabel("H min:")
        
        self.hMaxLabel = QLabel("H max:")
        self.kMinLabel = QLabel("K min:")
        self.kMaxLabel = QLabel("K max:")
        self.lMinLabel = QLabel("L min:")
        self.lMaxLabel = QLabel("L max:")
        
        self.hCenterLabel = QLabel("H center:")
        self.deltaHLabel = QLabel("Delta H:")
        self.kCenterLabel = QLabel("K center:")
        self.deltaKLabel = QLabel("Delta K:")
        self.lCenterLabel = QLabel("L center:")
        self.deltaLLabel = QLabel("Delta L:")
        
        self.hMinEdit = QSlider(Qt.Horizontal)
        self.hMinEdit.valueChanged.connect(lambda value: self.hMinLabel.setText(f"H min: {value / 100:.2f}"))
        self.hMaxEdit = QSlider(Qt.Horizontal)
        self.hMaxEdit.valueChanged.connect(lambda value: self.hMaxLabel.setText(f"H max: {value / 100:.2f}"))
        self.kMinEdit = QSlider(Qt.Horizontal)
        self.kMinEdit.valueChanged.connect(lambda value: self.kMinLabel.setText(f"K min: {value / 100:.2f}"))
        self.kMaxEdit = QSlider(Qt.Horizontal)
        self.kMaxEdit.valueChanged.connect(lambda value: self.kMaxLabel.setText(f"K max: {value / 100:.2f}"))
        self.lMinEdit = QSlider(Qt.Horizontal)
        self.lMinEdit.valueChanged.connect(lambda value: self.lMinLabel.setText(f"L min: {value / 100:.2f}"))
        self.lMaxEdit = QSlider(Qt.Horizontal)
        self.lMaxEdit.valueChanged.connect(lambda value: self.lMaxLabel.setText(f"L max: {value / 100:.2f}"))
        self.hCenterEdit = QSlider(Qt.Horizontal)
        self.hCenterEdit.valueChanged.connect(lambda value: self.hCenterLabel.setText(f"H center: {value / 100:.2f}"))
        self.deltaHEdit = QSlider(Qt.Horizontal)
        self.deltaHEdit.valueChanged.connect(lambda value: self.deltaHLabel.setText(f"Delta H: {value / 100:.2f}"))
        self.kCenterEdit = QSlider(Qt.Horizontal)
        self.kCenterEdit.valueChanged.connect(lambda value: self.kCenterLabel.setText(f"K center: {value / 100:.2f}"))
        self.deltaKEdit = QSlider(Qt.Horizontal)
        self.deltaKEdit.valueChanged.connect(lambda value: self.deltaKLabel.setText(f"Delta K: {value / 100:.2f}"))
        self.lCenterEdit = QSlider(Qt.Horizontal)
        self.lCenterEdit.valueChanged.connect(lambda value: self.lCenterLabel.setText(f"L center: {value / 100:.2f}"))
        self.deltaLEdit = QSlider(Qt.Horizontal)
        self.deltaLEdit.valueChanged.connect(lambda value: self.deltaLLabel.setText(f"Delta L: {value / 100:.2f}"))
        
        # Ensure consistent label width to prevent resizing
        self.hMinLabel.setMinimumWidth(100)
        self.hMaxLabel.setMinimumWidth(100)
        self.kMinLabel.setMinimumWidth(100)
        self.kMaxLabel.setMinimumWidth(100)
        self.lMinLabel.setMinimumWidth(100)
        self.lMaxLabel.setMinimumWidth(100)
        self.hCenterLabel.setMinimumWidth(100)
        self.deltaHLabel.setMinimumWidth(100)
        self.kCenterLabel.setMinimumWidth(100)
        self.deltaKLabel.setMinimumWidth(100)
        self.lCenterLabel.setMinimumWidth(100)
        self.deltaLLabel.setMinimumWidth(100)
        
        #set slider width
        self.hMinEdit.setMinimumWidth(300)
        self.hMaxEdit.setMinimumWidth(300)
        self.kMinEdit.setMinimumWidth(300)
        self.kMaxEdit.setMinimumWidth(300)
        self.lMinEdit.setMinimumWidth(300)
        self.lMaxEdit.setMinimumWidth(300)
        self.hCenterEdit.setMinimumWidth(300)
        self.deltaHEdit.setMinimumWidth(300)
        self.kCenterEdit.setMinimumWidth(300)
        self.deltaKEdit.setMinimumWidth(300)
        self.lCenterEdit.setMinimumWidth(300)
        self.deltaLEdit.setMinimumWidth(300)
        
        self.setHSliders(dataAxisMinMax, dataAxisResolutions)
        self.setKSliders(dataAxisMinMax, dataAxisResolutions)
        self.setLSliders(dataAxisMinMax, dataAxisResolutions)
        
        self.formLayout = QFormLayout()
        
        if self.currentHKLPlane == HKLPlaneEnum.H_K_Plane:
            label.setText("Options for Line Cut in H-K Plane:")
            self.initHKOptionsUI(dataAxisMinMax, dataAxisResolutions)
        elif self.currentHKLPlane == HKLPlaneEnum.H_L_Plane:
            label.setText("Options for Line Cut in H-L Plane:")
            self.initHLOptionsUI(dataAxisMinMax, dataAxisResolutions)
        elif self.currentHKLPlane == HKLPlaneEnum.K_L_Plane:
            label.setText("Options for Line Cut in K-L Plane:")
            self.initKLOptionsUI(dataAxisMinMax, dataAxisResolutions)
        
        
        layout.addWidget(label)
        layout.addLayout(self.formLayout)
        
        self.seePreview = QPushButton("See Preview")
        # self.seePreview.setChecked(False)
        self.seePreview.clicked.connect(lambda: self.onSeePreviewChanged())
        layout.addWidget(self.seePreview)
        self.previewHighlightLabel = QLabel("Preview of Highlighted Region:")
        self.previewHighlightFig = Figure(figsize=(8, 6))
        self.previewHighlightCanvas = FigureCanvas(self.previewHighlightFig)
        self.previewHighlightAx1 = self.previewHighlightFig.add_subplot(131)
        self.previewHighlightAx2 = self.previewHighlightFig.add_subplot(132)
        self.previewHighlightAx3 = self.previewHighlightFig.add_subplot(133)
        layout.addWidget(self.previewHighlightLabel)
        layout.addWidget(self.previewHighlightCanvas)
        self.previewIntegrationLabel = QLabel("Preview of Integration Window:")
        self.previewIntegrationFig = Figure(figsize=(8, 6))
        self.previewIntegrationCanvas = FigureCanvas(self.previewIntegrationFig)
        self.previewIntegrationAx1 = self.previewIntegrationFig.add_subplot(131)
        self.previewIntegrationAx2 = self.previewIntegrationFig.add_subplot(132)
        self.previewIntegrationAx3 = self.previewIntegrationFig.add_subplot(133)
        layout.addWidget(self.previewIntegrationLabel)
        layout.addWidget(self.previewIntegrationCanvas)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        self.setLayout(layout)
        
    def initHKOptionsUI(self, dataAxisMinMax, dataAxisResolutions):
        self.formLayout.addRow(self.hMinLabel, self.hMinEdit)
        self.formLayout.addRow(self.hMaxLabel, self.hMaxEdit)
        self.formLayout.addRow(self.kMinLabel, self.kMinEdit)
        self.formLayout.addRow(self.kMaxLabel, self.kMaxEdit)
        self.formLayout.addRow(self.lCenterLabel, self.lCenterEdit)
        self.formLayout.addRow(self.deltaLLabel, self.deltaLEdit)
        
    def initHLOptionsUI(self, dataAxisMinMax, dataAxisResolutions):
        self.formLayout.addRow(self.hMinLabel, self.hMinEdit)
        self.formLayout.addRow(self.hMaxLabel, self.hMaxEdit)
        self.formLayout.addRow(self.lMinLabel, self.lMinEdit)
        self.formLayout.addRow(self.lMaxLabel, self.lMaxEdit)
        self.formLayout.addRow(self.kCenterLabel, self.kCenterEdit)
        self.formLayout.addRow(self.deltaKLabel, self.deltaKEdit)
        
    def initKLOptionsUI(self, dataAxisMinMax, dataAxisResolutions):
        self.formLayout.addRow(self.kMinLabel, self.kMinEdit)
        self.formLayout.addRow(self.kMaxLabel, self.kMaxEdit)
        self.formLayout.addRow(self.lMinLabel, self.lMinEdit)
        self.formLayout.addRow(self.lMaxLabel, self.lMaxEdit)
        self.formLayout.addRow(self.hCenterLabel, self.hCenterEdit)
        self.formLayout.addRow(self.deltaHLabel, self.deltaHEdit)
        
    def setHSliders(self, dataAxisMinMax, dataAxisResolutions):
        self.hMinEdit.setMinimum(int(np.floor(dataAxisMinMax[0][0] * 100)))
        self.hMinEdit.setMaximum(int(np.ceil(dataAxisMinMax[0][1] * 100)))
        self.hMinEdit.setSingleStep(int(np.ceil(dataAxisResolutions[0] * 100)))
        self.hMinEdit.setValue(self.hMinEdit.minimum())

        self.hMaxEdit.setMinimum(int(np.floor(dataAxisMinMax[0][0] * 100)))
        self.hMaxEdit.setMaximum(int(np.ceil(dataAxisMinMax[0][1] * 100)))
        self.hMaxEdit.setSingleStep(int(np.ceil(dataAxisResolutions[0] * 100)))
        self.hMaxEdit.setValue(self.hMaxEdit.maximum())
        
        self.hCenterEdit.setMinimum(int(np.floor(dataAxisMinMax[0][0] * 100)))
        self.hCenterEdit.setMaximum(int(np.ceil(dataAxisMinMax[0][1] * 100)))
        self.hCenterEdit.setSingleStep(int(np.ceil(dataAxisResolutions[0] * 100)))
        self.hCenterEdit.setValue(int((dataAxisMinMax[0][0] + dataAxisMinMax[0][1]) / 2 * 100))
        self.deltaHEdit.setMinimum(0)
        self.deltaHEdit.setMaximum(int((dataAxisMinMax[0][1] - dataAxisMinMax[0][0]) * 100))
        self.deltaHEdit.setSingleStep(int(np.ceil(dataAxisResolutions[0] * 100)))
        self.deltaHEdit.setValue(int((dataAxisMinMax[0][1] - dataAxisMinMax[0][0]) * 100 / 10))
        
    def setKSliders(self, dataAxisMinMax, dataAxisResolutions):
        self.kMinEdit.setMinimum(int(np.floor(dataAxisMinMax[1][0] * 100)))
        self.kMinEdit.setMaximum(int(np.ceil(dataAxisMinMax[1][1] * 100)))
        self.kMinEdit.setSingleStep(int(np.ceil(dataAxisResolutions[1] * 100)))
        self.kMinEdit.setValue(self.kMinEdit.minimum())
        
        self.kMaxEdit.setMinimum(int(np.floor(dataAxisMinMax[1][0] * 100)))
        self.kMaxEdit.setMaximum(int(np.ceil(dataAxisMinMax[1][1] * 100)))
        self.kMaxEdit.setSingleStep(int(np.ceil(dataAxisResolutions[1] * 100)))
        self.kMaxEdit.setValue(self.kMaxEdit.maximum())
        
        self.kCenterEdit.setMinimum(int(np.floor(dataAxisMinMax[1][0] * 100)))
        self.kCenterEdit.setMaximum(int(np.ceil(dataAxisMinMax[1][1] * 100)))
        self.kCenterEdit.setSingleStep(int(np.ceil(dataAxisResolutions[1] * 100)))
        self.kCenterEdit.setValue(int((dataAxisMinMax[1][0] + dataAxisMinMax[1][1]) / 2 * 100))
        self.deltaKEdit.setMinimum(0)
        self.deltaKEdit.setMaximum(int((dataAxisMinMax[1][1] - dataAxisMinMax[1][0]) * 100))
        self.deltaKEdit.setSingleStep(int(np.ceil(dataAxisResolutions[1] * 100)))
        self.deltaKEdit.setValue(int((dataAxisMinMax[1][1] - dataAxisMinMax[1][0]) * 100 / 10))
        
    def setLSliders(self, dataAxisMinMax, dataAxisResolutions):
        self.lMinEdit.setMinimum(int(np.floor(dataAxisMinMax[2][0] * 100)))
        self.lMinEdit.setMaximum(int(np.ceil(dataAxisMinMax[2][1] * 100)))
        self.lMinEdit.setSingleStep(int(np.ceil(dataAxisResolutions[2] * 100)))
        self.lMinEdit.setValue(self.lMinEdit.minimum())
        
        self.lMaxEdit.setMinimum(int(np.floor(dataAxisMinMax[2][0] * 100)))
        self.lMaxEdit.setMaximum(int(np.ceil(dataAxisMinMax[2][1] * 100)))
        self.lMaxEdit.setSingleStep(int(np.ceil(dataAxisResolutions[2] * 100)))
        self.lMaxEdit.setValue(self.lMaxEdit.maximum())
        
        self.lCenterEdit.setMinimum(int(np.floor(dataAxisMinMax[2][0] * 100)))
        self.lCenterEdit.setMaximum(int(np.ceil(dataAxisMinMax[2][1] * 100)))
        self.lCenterEdit.setSingleStep(int(np.ceil(dataAxisResolutions[2] * 100)))
        self.lCenterEdit.setValue(int((dataAxisMinMax[2][0] + dataAxisMinMax[2][1]) / 2 * 100))
        self.deltaLEdit.setMinimum(0)
        self.deltaLEdit.setMaximum(int((dataAxisMinMax[2][1] - dataAxisMinMax[2][0]) * 100))
        self.deltaLEdit.setSingleStep(int(np.ceil(dataAxisResolutions[2] * 100)))
        self.deltaLEdit.setValue(int((dataAxisMinMax[2][1] - dataAxisMinMax[2][0]) * 100 / 10))
        
    def onSeePreviewChanged(self):
        # Placeholder for handling see preview option change
        if self.mousePos is None:
            QMessageBox.warning(self, "Preview unavailable", "No line position selected on the main plot.")
            return

        scissors = Scissors()
        print(f"data: {self.currentData.tree}")
        scissors.set_data(self.currentData)
        if self.currentHKLPlane == HKLPlaneEnum.H_K_Plane:
            hMin = self.hMinEdit.value() / 100
            hMax = self.hMaxEdit.value() / 100
            kMin = self.kMinEdit.value() / 100
            kMax = self.kMaxEdit.value() / 100
            lCenter = self.lCenterEdit.value() / 100
            deltaL = self.deltaLEdit.value() / 100
            h_half = (hMax - hMin) / 2
            k_half = (kMax - kMin) / 2
            l_half = deltaL / 2
            if h_half <= 0 or k_half <= 0 or l_half <= 0:
                QMessageBox.warning(self, "Invalid preview window", "Set min/max ranges and delta values so all integration widths are > 0.")
                return
            scissors.set_center((self.mousePos[0], self.mousePos[1], lCenter))  # Assuming the line cut is in the H-K plane for simplicity
            scissors.set_window((h_half, k_half, l_half))
        elif self.currentHKLPlane == HKLPlaneEnum.H_L_Plane:
            hMin = self.hMinEdit.value() / 100
            hMax = self.hMaxEdit.value() / 100
            lMin = self.lMinEdit.value() / 100
            lMax = self.lMaxEdit.value() / 100
            kCenter = self.kCenterEdit.value() / 100
            deltaK = self.deltaKEdit.value() / 100
            h_half = (hMax - hMin) / 2
            l_half = (lMax - lMin) / 2
            k_half = deltaK / 2
            if h_half <= 0 or l_half <= 0 or k_half <= 0:
                QMessageBox.warning(self, "Invalid preview window", "Set min/max ranges and delta values so all integration widths are > 0.")
                return
            scissors.set_center((self.mousePos[0], kCenter, self.mousePos[1]))  # Assuming the line cut is in the H-L plane for simplicity
            scissors.set_window((h_half, k_half, l_half))
        elif self.currentHKLPlane == HKLPlaneEnum.K_L_Plane:
            kMin = self.kMinEdit.value() / 100
            kMax = self.kMaxEdit.value() / 100
            lMin = self.lMinEdit.value() / 100
            lMax = self.lMaxEdit.value() / 100
            hCenter = self.hCenterEdit.value() / 100
            deltaH = self.deltaHEdit.value() / 100
            k_half = (kMax - kMin) / 2
            l_half = (lMax - lMin) / 2
            h_half = deltaH / 2
            if k_half <= 0 or l_half <= 0 or h_half <= 0:
                QMessageBox.warning(self, "Invalid preview window", "Set min/max ranges and delta values so all integration widths are > 0.")
                return
            scissors.set_center((hCenter, self.mousePos[0], self.mousePos[1]))  # Assuming the line cut is in the K-L plane for simplicity
            scissors.set_window((h_half, k_half, l_half))
        
        try:
            linecut = scissors.cut_data()
        except Exception as exc:
            QMessageBox.critical(self, "Preview failed", f"Could not compute line cut preview.\n{exc}")
            return
        print(scissors.integration_window)
        
        #show preview in dialogue: 
        p1, p2, p3 = scissors.highlight_integration_window()
        self.previewHighlightAx1.clear()
        self.previewHighlightAx2.clear()
        self.previewHighlightAx3.clear()
        
        X1, Y1, Z1 = self.extract_quadmesh_data(p1)
        X2, Y2, Z2 = self.extract_quadmesh_data(p2)
        X3, Y3, Z3 = self.extract_quadmesh_data(p3)
        
        # quadmesh1 = self.previewHighlightAx.pcolormesh(X1, Y1, Z1, shading='auto')
        #plot on subplot 111
        quadmesh1 = self.previewHighlightAx1.pcolormesh(X1, Y1, Z1, shading='auto', cmap='viridis')
        quadmesh2 = self.previewHighlightAx2.pcolormesh(X2, Y2, Z2, shading='auto', cmap='viridis')
        quadmesh3 = self.previewHighlightAx3.pcolormesh(X3, Y3, Z3, shading='auto', cmap='viridis')
        
        
        self.previewHighlightAx1.set_title("Highlighted Integration Window")
        self.previewHighlightAx2.set_title("Highlighted Integration Window")
        self.previewHighlightAx3.set_title("Highlighted Integration Window")
        self.previewHighlightCanvas.draw()

        p4, p5, p6 = scissors.plot_integration_window()
        self.previewIntegrationAx1.clear()
        self.previewIntegrationAx2.clear()
        self.previewIntegrationAx3.clear()
        
        # Plot the integration window regions if they have valid data
        X4, Y4, Z4 = self.extract_quadmesh_data(p4)
        X5, Y5, Z5 = self.extract_quadmesh_data(p5)
        X6, Y6, Z6 = self.extract_quadmesh_data(p6)
        quadmesh4 = self.previewIntegrationAx1.pcolormesh(X4, Y4, Z4, shading='auto', cmap='viridis')
        quadmesh5 = self.previewIntegrationAx2.pcolormesh(X5, Y5, Z5, shading='auto', cmap='viridis')
        quadmesh6 = self.previewIntegrationAx3.pcolormesh(X6, Y6, Z6, shading='auto', cmap='viridis')
        
        
        self.previewIntegrationAx1.set_title("Integration Window")
        self.previewIntegrationAx2.set_title("Integration Window")
        self.previewIntegrationAx3.set_title("Integration Window")
        self.previewIntegrationCanvas.draw()
            
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
        
    def getLineCutOptions(self):
        # Placeholder for retrieving options
        return {
            "h_min": self.hMinEdit.value() / 100,
            "h_max": self.hMaxEdit.value() / 100,
            "k_min": self.kMinEdit.value() / 100,
            "k_max": self.kMaxEdit.value() / 100,
            "l_min": self.lMinEdit.value() / 100,
            "l_max": self.lMaxEdit.value() / 100,
            "h_center": self.hCenterEdit.value() / 100,
            "delta_h": self.deltaHEdit.value() / 100,
            "k_center": self.kCenterEdit.value() / 100,
            "delta_k": self.deltaKEdit.value() / 100,
            "l_center": self.lCenterEdit.value() / 100,
            "delta_l": self.deltaLEdit.value() / 100
        }