# AP 2026
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QDoubleSpinBox, QLabel, QPushButton, QComboBox
from PyQt5.QtCore import pyqtSignal, Qt
import numpy as np

class AnalysisOptionsWidget(QWidget):
    fitLineCut = pyqtSignal(bool, float)  # Signal to indicate Gaussian filter state and sigma value
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        # Gaussian Filter Options
        self.fitLineCutCheckBox = QCheckBox("Fit LineCut")
        self.fitLineCutCheckBox.stateChanged.connect(self.onFitLineCutStateChanged)
        
        self.FitTypeLabel = QLabel("FitType: ")
        # self.sigmaSpinBox = QDoubleSpinBox()
        # self.sigmaSpinBox.setRange(0.1, 10.0)
        # self.sigmaSpinBox.setSingleStep(0.1)
        # self.sigmaSpinBox.setValue(1.0)
        # self.sigmaSpinBox.valueChanged.connect(self.onSigmaValueChanged)
        self.FitType = QComboBox()
        self.FitType.addItems(["Gaussian", "Lorentzian", "Voigt"])
        self.FitType.currentTextChanged.connect(self.onFitTypeChanged)
        
        sigmaLayout = QHBoxLayout()
        sigmaLayout.addWidget(self.FitTypeLabel)
        sigmaLayout.addWidget(self.FitType)
        
        layout.addWidget(self.fitLineCutCheckBox)
        layout.addLayout(sigmaLayout)
        
        self.setLayout(layout)
        
    def onFitLineCutStateChanged(self, state):
        isChecked = (state == Qt.Checked)
        sigmaValue = self.sigmaSpinBox.value()
        print(f"Fit LineCut state changed: {isChecked}, Sigma: {sigmaValue}")
        self.fitLineCut.emit(isChecked, sigmaValue)
        
    def onFitTypeChanged(self, value):
        isChecked = self.fitLineCutCheckBox.isChecked()
        print(f"FitType changed: {value}, Fit LineCut is {'enabled' if isChecked else 'disabled'}")
        self.fitLineCut.emit(isChecked, value)