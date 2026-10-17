# AP 2026
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QDoubleSpinBox, QLabel, QPushButton, QComboBox
from PyQt5.QtCore import pyqtSignal, Qt
import numpy as np

class AnalysisOptionsWidget(QWidget):
    fitLineCut = pyqtSignal(str, list)  # Signal to indicate Gaussian filter state and sigma value
    
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
        self.FitType.addItems(["Model", "Composite", "List Of Models"])
        
        self.modelType = QComboBox()
        self.modelType.setVisible(True)
        
        sigmaLayout = QHBoxLayout()
        sigmaLayout.addWidget(self.FitTypeLabel)
        sigmaLayout.addWidget(self.FitType)
        
        layout.addWidget(self.fitLineCutCheckBox)
        layout.addLayout(sigmaLayout)
        
        # Container for composite model rows
        self.compositeContainer = QWidget()
        self.compositeLayout = QVBoxLayout()
        self.compositeLayout.setContentsMargins(0, 0, 0, 0)
        self.compositeContainer.setLayout(self.compositeLayout)
        self.compositeContainer.setVisible(False)  # hidden until "Composite" is selected
        
        self.initModelFitTypeOptions()
        self.initCompositeFitTypeOptions()
        self.FitType.currentTextChanged.connect(self.onFitTypeChanged)
        
        layout.addWidget(self.modelType)
        layout.addWidget(self.compositeContainer)
        
        self.submitFitParamsButton = QPushButton("Submit Fit Parameters")
        self.submitFitParamsButton.clicked.connect(self.onSubmitFitParams)
        layout.addWidget(self.submitFitParamsButton)
        
        self.setLayout(layout)
        
    def initModelFitTypeOptions(self):
        """Initialize model fit type options"""
        self.modelType.addItems(["Gaussian", "Linear"])
        self.modelType.setCurrentText("Gaussian")
        self.modelType.currentTextChanged.connect(self.onModelTypeChanged)
        
    def onModelTypeChanged(self, value):
        print(f"Model type changed: {value}")
        
    def initCompositeFitTypeOptions(self):
        """Initialize composite fit type options with a dynamic list of combo boxes."""
        self.compositeModels = []  # list of QComboBox references
        self.MODEL_OPTIONS = ["Gaussian", "Linear"]
        
        self.addCompositeButton = QPushButton("+ Add Model")
        self.addCompositeButton.clicked.connect(self.addCompositeModelRow)
        self.compositeLayout.addWidget(self.addCompositeButton)
        
        # Start with one row by default
        self.addCompositeModelRow()
    
    def addCompositeModelRow(self):
        """Add a new combo box row to the composite model list."""
        rowWidget = QWidget()
        rowLayout = QHBoxLayout()
        rowLayout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(f"Model {len(self.compositeModels) + 1}:")
        comboBox = QComboBox()
        comboBox.addItems(self.MODEL_OPTIONS)
        comboBox.currentTextChanged.connect(lambda val: self.onCompositeModelChanged())
        
        removeButton = QPushButton("✕")
        removeButton.setFixedWidth(30)
        removeButton.clicked.connect(lambda: self.removeCompositeModelRow(rowWidget, comboBox))
        
        rowLayout.addWidget(label)
        rowLayout.addWidget(comboBox)
        rowLayout.addWidget(removeButton)
        rowWidget.setLayout(rowLayout)
        
        # Insert the row before the "Add" button
        self.compositeLayout.insertWidget(self.compositeLayout.count() - 1, rowWidget)
        self.compositeModels.append(comboBox)
        
        self.onCompositeModelChanged()
    
    def removeCompositeModelRow(self, rowWidget, comboBox):
        """Remove a composite model row."""
        if len(self.compositeModels) <= 1:
            return  # keep at least one row
        
        self.compositeModels.remove(comboBox)
        self.compositeLayout.removeWidget(rowWidget)
        rowWidget.deleteLater()
        
        # Re-label remaining rows
        for i, widget in enumerate(self.compositeModels):
            label = widget.parent().findChild(QLabel)
            if label:
                label.setText(f"Model {i + 1}:")
        
        self.onCompositeModelChanged()
    
    def getCompositeModelList(self):
        """Return the list of currently selected composite models."""
        return [cb.currentText() for cb in self.compositeModels]
    
    def onCompositeModelChanged(self):
        """Called whenever any composite model combo box changes."""
        models = self.getCompositeModelList()
        print(f"Composite models: {models}")
        
    def onFitLineCutStateChanged(self, state):
        isChecked = (state == Qt.Checked)
        print(f"Fit LineCut state changed: {isChecked}")
        
    def onFitTypeChanged(self, value):
        isChecked = self.fitLineCutCheckBox.isChecked()
        print(f"FitType changed: {value}, Fit LineCut is {'enabled' if isChecked else 'disabled'}")
        # Show/hide the composite container based on selection
        self.compositeContainer.setVisible(value == "Composite" or value == "List Of Models")
        self.modelType.setVisible(value == "Model")
        
    def onSubmitFitParams(self):
        fitType = self.FitType.currentText()
        modelType = self.modelType.currentText() if fitType == "Model" else None
        compositeModels = self.getCompositeModelList() if fitType == "Composite" or fitType == "List Of Models" else None
        print(f"Submitting Fit Parameters: FitType={fitType}, ModelType={modelType}, CompositeModels={compositeModels}")
        self.fitLineCut.emit(fitType, compositeModels if compositeModels else [modelType] if modelType else [])