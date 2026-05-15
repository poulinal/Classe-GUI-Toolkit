# AP 2026

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLineEdit, QWidget, QComboBox, QLabel
from PyQt5.QtCore import QDir, QTimer, pyqtSignal
import os
import numpy as np

from CGTProject.utilities.HKLPlaneEnum import HKLPlaneEnum

from nxs_analysis_tools.datasets import cubic

class FileManagerWidget(QWidget):
    pathSelected = pyqtSignal(tuple)  # Emits (dataPathRoot, transformFiles) - Tuple[str, List]
    submitOptions = pyqtSignal()
    # temperatureChanged = pyqtSignal(str)  # Emits selected temperature value as str
    # hklPlaneChanged = pyqtSignal(str)  # Emits selected HKL plane as str
    
    def __init__(self, lastDirectory : str = ''):
        super().__init__()
        self.lastDirectory: str = str(lastDirectory or '')
        self.folderDataPath : str = self.lastDirectory
        self.selectedSampleType : str = ""
        self.selectedSample : str = ""

        self._collapsed: bool = False
        
        # self.temperatureSelected : str = ""
        # self.hklPlaneSelected : str = ""
        
        self.setupWidget(lastDirectory)
        
    #returns the path of the folder selected by the user
    def setupWidget(self, lastDirectory : str = ''):
        fileManagerLayout = QVBoxLayout()

        self.toggleCollapseButton = QPushButton('Collapse')
        self.toggleCollapseButton.clicked.connect(self._onToggleCollapseClicked)

        self.selectionSummaryLineEdit = QLineEdit()
        self.selectionSummaryLineEdit.setReadOnly(True)
        self.selectionSummaryLineEdit.setPlaceholderText('No selection')
        
        self.folderDataPathLineEdit = QLineEdit()
        if self.folderDataPath:
            self.folderDataPathLineEdit.setText(self.folderDataPath)
        self.browseButton = QPushButton('Browse')
        
        self.selectSampleTypeCombo = QComboBox()
        self.selectSampleTypeCombo.hide()
        
        self.selectSampleCombo = QComboBox()
        self.selectSampleCombo.hide()
        
        self.useAGeneratedDatasetButton = QPushButton('Use a Generated Dataset')
        # useVacancyGeneratedDataset = QPushButton('Use a Generated Diffuse Scattering Dataset')
        
        self.submitButton = QPushButton('Submit')

        getFolderPathLayout = QHBoxLayout()
        getFolderPathLayout.addWidget(self.folderDataPathLineEdit)
        getFolderPathLayout.addWidget(self.browseButton)
        
        
        self.browseButton.clicked.connect(self._onBrowseButtonClicked)
        self.selectSampleTypeCombo.currentIndexChanged.connect(self._onSampleTypeComboChanged)
        self.selectSampleCombo.currentIndexChanged.connect(self._onSampleComboChanged)
        self.folderDataPathLineEdit.editingFinished.connect(lambda: self.browsePath(lastDirectory))
        
        self.changeTemperatureCombo = QComboBox()
        self.changeTemperatureCombo.setEnabled(False)
        self.changeTemperatureCombo.currentIndexChanged.connect(lambda _: self._updateSelectionSummary())
        
        self.selectHKLPlaneCombo = QComboBox()
        self.selectHKLPlaneCombo.addItems(HKLPlaneEnum.list())
        self.selectHKLPlaneCombo.setEnabled(False)
        self.selectHKLPlaneCombo.currentIndexChanged.connect(lambda _: self._updateSelectionSummary())
        
        self.useAGeneratedDatasetButton.clicked.connect(self._onUseAGeneratedDatasetClicked)
        # useVacancyGeneratedDataset.clicked.connect(self._onUseVacancyGeneratedDatasetClicked)
        self.submitButton.clicked.connect(self._onSubmitButtonClicked)
        self.submitButton.setEnabled(False)
        
        fileManagerLayout.addWidget(self.toggleCollapseButton)
        fileManagerLayout.addWidget(self.selectionSummaryLineEdit)

        fileManagerLayout.addLayout(getFolderPathLayout)
        fileManagerLayout.addWidget(self.selectSampleTypeCombo)
        fileManagerLayout.addWidget(self.selectSampleCombo)
        self.selectTemperatureLabel = QLabel("Select Temperature:")
        fileManagerLayout.addWidget(self.selectTemperatureLabel)
        fileManagerLayout.addWidget(self.changeTemperatureCombo)
        fileManagerLayout.addWidget(self.selectHKLPlaneCombo)
        fileManagerLayout.addWidget(self.useAGeneratedDatasetButton)
        # fileManagerLayout.addWidget(useVacancyGeneratedDataset)
        fileManagerLayout.addWidget(self.submitButton)
        self.setLayout(fileManagerLayout)

        self._updateSelectionSummary()
        QTimer.singleShot(0, self._tryInitializeFromLastDirectory)

    def _tryInitializeFromLastDirectory(self):
        """If a previous data folder exists, pre-populate sample selectors and emit pathSelected."""
        if not self.folderDataPath or not os.path.isdir(self.folderDataPath):
            return

        self.selectSampleTypeCombo.show()
        self.populateSampleTypeCombo(self.folderDataPath)

        if self.selectSampleTypeCombo.count() == 0:
            return

        # Ensure downstream handlers run even when index stays at 0.
        self._onSampleTypeComboChanged(self.selectSampleTypeCombo.currentIndex())

        if self.selectSampleCombo.count() == 0:
            return

        self._onSampleComboChanged(self.selectSampleCombo.currentIndex())
        # self.pathSelected.emit((self.getSelectedSamplePath(), self.getAllSelectedSamplePaths()))

    def _onBrowseButtonClicked(self):
        """Handle browse button click event"""
        self.folderDataPath = self.browsePath(self.lastDirectory)
        if self.folderDataPath:
            self.lastDirectory = self.folderDataPath
        self.folderDataPathLineEdit.setText(self.folderDataPath)
        self._updateSelectionSummary()
        if self.getFolderDataPath() != '':
            self.selectSampleTypeCombo.show()
            self.populateSampleTypeCombo(self.getFolderDataPath())
            self._onSampleTypeComboChanged(self.selectSampleTypeCombo.currentIndex())
            
    def _onSampleTypeComboChanged(self, index):
        """Handle sample combo box selection change event"""
        self.selectedSampleType = self.selectSampleTypeCombo.currentText()
        self.selectSampleCombo.show()
        self.populateSampleCombo(self.getSelectedSampleTypePath())
        self._updateSelectionSummary()
        
    def _onSampleComboChanged(self, index):
        """Handle sample combo box selection change event"""
        self.selectedSample = self.selectSampleCombo.currentText()
        
        metadata_files = self.getAllSelectedSamplePaths()
        self.pathSelected.emit((self.getSelectedSamplePath(), metadata_files))
        self.submitButton.setEnabled(True)
        self._updateSelectionSummary()
        
    def _onUseAGeneratedDatasetClicked(self):
        """Handle use a generated dataset button click event"""
        # Using the standard nxrefine filepath:
        # data = load_transform('experimentname/nxrefine/samplename/labelname/samplename_15.nxs')

        # Loading an example dataset
        sample_directory = cubic(temperatures=[15]) # Download the example dataset to cache directory
        sample_files = f'{sample_directory}/cubic_15.nxs'
        print(f"Using generated dataset at: {sample_files}")
        self.pathSelected.emit( (sample_directory, [sample_files]) )
        self.submitButton.setEnabled(True)
        self.folderDataPath = sample_directory
        self.lastDirectory = sample_directory
        self.folderDataPathLineEdit.setText(self.folderDataPath)
        self.selectedSampleType = ""
        self.selectedSample = ""
        self._updateSelectionSummary()
        # data = load_transform(f'{sample_directory}/cubic_15.nxs')
        
    # def _onUseVacancyGeneratedDatasetClicked(self):
    #     """Handle use a generated diffuse scattering dataset button click event"""
    #     # Loading an example dataset
    #     from nxs_analysis_tools.datasets import vacancies
    #     from nxs_analysis_tools.datareduction import load_discus_nxs

    #     data_path = vacancies()
    #     sample_directory = os.path.dirname(data_path)
    #     print(f"Using generated diffuse scattering dataset at: {data_path}")
    #     sample_files = data_path
    #     self.pathSelected.emit( (sample_directory, [sample_files]) )
    #     self.submitButton.setEnabled(True)
        
    def _onSubmitButtonClicked(self):
        """Handle submit button click event"""
        # [transform_files, metadata_files] = self.getAllSelectedSamplePaths()
        # self.pathSelected.emit((self.getSelectedSamplePath(), transform_files, metadata_files))
        # metadata_files = self.getAllSelectedSamplePaths()
        # self.pathSelected.emit((self.getSelectedSamplePath(), metadata_files))
        self.submitOptions.emit()
        
    def setFileOptionsEnabled(self, enabled: bool):
        """Enables or disables file options widgets

        Args:
            enabled (bool): True to enable, False to disable
        """
        self.changeTemperatureCombo.setEnabled(enabled)
        self.selectHKLPlaneCombo.setEnabled(enabled)
            
    def populateSampleTypeCombo(self, folderPath: str):
        """Populates the sample selection combo box with sample names from the given folder path #i.e. like FeSc2S4

        Args:
            folderPath (str): Path to the folder containing sample data
        """
        ignoreNames : list[str] = ['calibrations', 'metadata', 'configurations', 'tasks', 'scripts']
        self.selectSampleTypeCombo.clear()
        try:
            sampleNames = [name for name in os.listdir(folderPath) if os.path.isdir(os.path.join(folderPath, name)) and name not in ignoreNames]
            self.selectSampleTypeCombo.addItems(sampleNames)
        except Exception as e:
            print(f"Error populating sample combo: {e}")
            
    def populateSampleCombo(self, sampleTypePath: str):
        """Populates the sample selection combo box with sample names from the given sample type path #i.e. like Sample1

        Args:
            sampleTypePath (str): Path to the folder containing specific sample type data
        """
        self.selectSampleCombo.clear()
        try:
            sampleNames = [name for name in os.listdir(sampleTypePath) if os.path.isdir(os.path.join(sampleTypePath, name))]
            self.selectSampleCombo.addItems(sampleNames)
        except Exception as e:
            print(f"Error populating sample combo: {e}")
            
    def populateTemperatureCombo(self, temperatureValues: list[str]):
        """Populates the temperature selection combo box with temperature values

        Args:
            temperatureValues (list[str] | list[tuple[str, str]]): Display labels or (label, value) pairs
        """
        self.changeTemperatureCombo.clear()
        try:
            if temperatureValues and isinstance(temperatureValues[0], tuple):
                for display_text, value in temperatureValues:
                    self.changeTemperatureCombo.addItem(str(display_text), value)
            else:
                for value in temperatureValues:
                    self.changeTemperatureCombo.addItem(str(value), str(value))
            self._updateSelectionSummary()
        except Exception as e:
            print(f"Error populating temperature combo: {e}")

    def _onToggleCollapseClicked(self):
        self._setCollapsed(not self._collapsed)

    def _setCollapsed(self, collapsed: bool):
        self._collapsed = collapsed
        self.toggleCollapseButton.setText('Expand' if self._collapsed else 'Collapse')

        # Keep only the toggle and summary visible when collapsed.
        visible = not self._collapsed
        self.folderDataPathLineEdit.setVisible(visible)
        self.browseButton.setVisible(visible)
        self.selectSampleTypeCombo.setVisible(visible)
        self.selectSampleCombo.setVisible(visible)
        self.selectTemperatureLabel.setVisible(visible)
        self.changeTemperatureCombo.setVisible(visible)
        self.selectHKLPlaneCombo.setVisible(visible)
        self.useAGeneratedDatasetButton.setVisible(visible)
        self.submitButton.setVisible(visible)

        # Ensure summary is up to date.
        self._updateSelectionSummary()

    def _updateSelectionSummary(self):
        parts = []
        if self.folderDataPath:
            parts.append(f"Folder: {os.path.basename(self.folderDataPath) or self.folderDataPath}")
        if self.selectedSampleType:
            parts.append(f"Type: {self.selectedSampleType}")
        if self.selectedSample:
            parts.append(f"Sample: {self.selectedSample}")

        temp = self.changeTemperatureCombo.currentText().strip() if self.changeTemperatureCombo.count() else ""
        if temp:
            parts.append(f"T: {temp}")

        plane = self.selectHKLPlaneCombo.currentText().strip() if self.selectHKLPlaneCombo.count() else ""
        if plane and self.selectHKLPlaneCombo.isEnabled():
            parts.append(f"Plane: {plane}")

        summary = " | ".join(parts)
        self.selectionSummaryLineEdit.setText(summary)
            
    def getTemperatureComboValue(self) -> str:
        current_data = self.changeTemperatureCombo.currentData()
        if current_data is not None:
            return str(current_data)
        return self.changeTemperatureCombo.currentText()
    
    def getHKLPlaneComboValue(self) -> str:
        return self.selectHKLPlaneCombo.currentText()

    def browsePath(self, lastDirectory : str = '') -> str:
        """setups the file dialog to select a directory and sets the path_type to the selected directory

        Args:
            path_type (QLineEdit): QLineEdit whose text will be set to the selected directory
        """
        start_dir = lastDirectory or self.lastDirectory or QDir().homePath()

        path = QFileDialog.getExistingDirectory(
        #path = getOpenFilesAndDirs(
            #parent=self,
            caption = "Select directory of sample named 'nxrefine'",
            directory = start_dir,
            options = QFileDialog.Option.DontUseNativeDialog,
            # filter = "Directory (*/nxrefine/)"
        )
        # self.pathSelected.emit(path)
        print(f"From filedialog we get path: {path}")
        if path:
            self.lastDirectory = path
        return path
    
    def getFolderDataPath(self):
        return self.folderDataPath
    
    def getSelectedSampleTypePath(self):
        sampleTypePath = os.path.join(self.getFolderDataPath(), self.selectedSampleType)
        return sampleTypePath
    
    def getSelectedSamplePath(self):
        samplePath = os.path.join(self.getSelectedSampleTypePath(), self.selectedSample)
        return samplePath
    
    def getAllSelectedSamplePaths(self):
        # Returns a list of all file paths in the selected sample directory
        samplePath = self.getSelectedSamplePath()
        print(f"selected sample path: {samplePath}")
        # metadata are in the samplePath root folder named: '{sampleTypePath}_{temperature}.nxs
        metadata_files = [os.path.join(samplePath, file) for file in os.listdir(samplePath) if file.endswith('.nxs')]
        print(f"metadata files: {metadata_files}")
        # for root, dirs, files in os.walk(samplePath):
        #     filePaths = [os.path.join(root, file) for file in files]
        # print(f"all filepaths: {filePaths}")
        # transform files are in each temperature folder named exactly: 'transform.nxs'
        # transform_files = [file for file in filePaths if file.endswith('/transform.nxs')]
        # return [metadata_files, transform_files]
        return metadata_files