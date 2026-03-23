# AP 2026

'''
 options widget to generate delta PDF from temperature dependent scattering data
#need scrollable options with previews and results along the way for:
--setup
- lattice params

--mask options
- option to choose either bragg mask or intensity mask
- bragg mask peak punch radius
- bragg mask coeffs
- bragg mask thresh
- intensity mask thresh
- intensity mask radius
- generate mask at coords

--setup kernal
- option to choose kernal (only gaussian for right now)
- options for that kernal (kernal dependant)

--set taper for window
- choose window type (set_ellipsoidal_tukey_window, set_tukey_window, set_hexagonal_tukey_window)
- set turkey alphas

--setup padding
- choose padding triple tuple

--submit to preform FFT

'''
#also allow logscale option for plottedGraphWidget

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QDoubleSpinBox, QLabel, QPushButton, QComboBox
from PyQt5.QtCore import pyqtSignal, Qt
import numpy as np

from nxs_analysis_tools.pairdistribution import DeltaPDF

class DeltaPDFOptionsWidget(QDialogue):
    generateDeltaPDF = pyqtSignal(dict)  # Signal to indicate Gaussian filter state and sigma value
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        # Gaussian Filter Options
        self.generateDeltaPDFCheckBox = QCheckBox("Generate Delta PDF")
        self.generateDeltaPDFCheckBox.stateChanged.connect(self.onGenerateDeltaPDFStateChanged)
        
        self.optionsLabel = QLabel("Options: ")
        self.optionsComboBox = QComboBox()
        self.optionsComboBox.addItems(["Option 1", "Option 2", "Option 3"])
        
        optionsLayout = QHBoxLayout()
        optionsLayout.addWidget(self.optionsLabel)
        optionsLayout.addWidget(self.optionsComboBox)
        
        layout.addWidget(self.generateDeltaPDFCheckBox)
        layout.addLayout(optionsLayout)
        
        self.setLayout(layout)
        
    def onGenerateDeltaPDFStateChanged(self, state):
        isChecked = state == Qt.Checked
        selectedOption = self.optionsComboBox.currentText()
        print(f"Generate Delta PDF: {isChecked}, Selected Option: {selectedOption}")
        self.generateDeltaPDF.emit({"generate": isChecked, "option": selectedOption})