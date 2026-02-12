# AP 2026

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLineEdit, QWidget, QComboBox, QLabel
from PyQt5.QtCore import QDir, pyqtSignal
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
        self.folderDataPath : str = ""
        self.selectedSampleType : str = ""
        self.selectedSample : str = ""
        
        # self.temperatureSelected : str = ""
        # self.hklPlaneSelected : str = ""
        
        self.setupWidget(lastDirectory)
        
    #returns the path of the folder selected by the user
    def setupWidget(self, lastDirectory : str = ''):
        fileManagerLayout = QVBoxLayout()
        
        self.folderDataPathLineEdit = QLineEdit()
        browseButton = QPushButton('Browse')
        
        self.selectSampleTypeCombo = QComboBox()
        self.selectSampleTypeCombo.hide()
        
        self.selectSampleCombo = QComboBox()
        self.selectSampleCombo.hide()
        
        useAGeneratedDataset = QPushButton('Use a Generated Dataset')
        
        self.submitButton = QPushButton('Submit')

        getFolderPathLayout = QHBoxLayout()
        getFolderPathLayout.addWidget(self.folderDataPathLineEdit)
        getFolderPathLayout.addWidget(browseButton)
        
        
        browseButton.clicked.connect(self._onBrowseButtonClicked)
        self.selectSampleTypeCombo.currentIndexChanged.connect(self._onSampleTypeComboChanged)
        self.selectSampleCombo.currentIndexChanged.connect(self._onSampleComboChanged)
        self.folderDataPathLineEdit.editingFinished.connect(lambda: self.browsePath(lastDirectory))
        
        self.changeTemperatureCombo = QComboBox()
        self.changeTemperatureCombo.setEnabled(False)
        # self.changeTemperatureCombo.currentIndexChanged.connect(lambda index: self.temperatureChanged.emitself.getTemperatureComboValue()))
        
        self.selectHKLPlaneCombo = QComboBox()
        self.selectHKLPlaneCombo.addItems(HKLPlaneEnum.list())
        self.selectHKLPlaneCombo.setEnabled(False)
        # self.selectHKLPlaneCombo.currentIndexChanged.connect(lambda index: self.hklPlaneChanged.emit(self.selectHKLPlaneCombo.currentText()))
        
        useAGeneratedDataset.clicked.connect(self._onUseAGeneratedDatasetClicked)
        self.submitButton.clicked.connect(self._onSubmitButtonClicked)
        self.submitButton.setEnabled(False)
        
        fileManagerLayout.addLayout(getFolderPathLayout)
        fileManagerLayout.addWidget(self.selectSampleTypeCombo)
        fileManagerLayout.addWidget(self.selectSampleCombo)
        fileManagerLayout.addWidget(QLabel("Select Temperature:"))
        fileManagerLayout.addWidget(self.changeTemperatureCombo)
        fileManagerLayout.addWidget(self.selectHKLPlaneCombo)
        fileManagerLayout.addWidget(useAGeneratedDataset)
        fileManagerLayout.addWidget(self.submitButton)
        self.setLayout(fileManagerLayout)

    def _onBrowseButtonClicked(self):
        """Handle browse button click event"""
        self.folderDataPath = self.browsePath()
        self.folderDataPathLineEdit.setText(self.folderDataPath)
        if self.getFolderDataPath() != '':
            self.selectSampleTypeCombo.show()
            self.populateSampleTypeCombo(self.getFolderDataPath())
            
    def _onSampleTypeComboChanged(self, index):
        """Handle sample combo box selection change event"""
        self.selectedSampleType = self.selectSampleTypeCombo.currentText()
        self.selectSampleCombo.show()
        self.populateSampleCombo(self.getSelectedSampleTypePath())
        
    def _onSampleComboChanged(self, index):
        """Handle sample combo box selection change event"""
        self.selectedSample = self.selectSampleCombo.currentText()
        
        metadata_files = self.getAllSelectedSamplePaths()
        self.pathSelected.emit((self.getSelectedSamplePath(), metadata_files))
        self.submitButton.setEnabled(True)
        
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
        # data = load_transform(f'{sample_directory}/cubic_15.nxs')
        
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
        """Populates the sample selection combo box with sample names from the given folder path

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
        """Populates the sample selection combo box with sample names from the given sample type path

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
            temperatureValues (list[str]): List of temperature values as strings
        """
        self.changeTemperatureCombo.clear()
        try:
            self.changeTemperatureCombo.addItems(temperatureValues)
        except Exception as e:
            print(f"Error populating temperature combo: {e}")
            
    def getTemperatureComboValue(self) -> str:
        return self.changeTemperatureCombo.currentText()
    
    def getHKLPlaneComboValue(self) -> str:
        return self.selectHKLPlaneCombo.currentText()

    def browsePath(self, lastDirectory : str = QDir().homePath()) -> str:
        """setups the file dialog to select a directory and sets the path_type to the selected directory

        Args:
            path_type (QLineEdit): QLineEdit whose text will be set to the selected directory
        """
        path = QFileDialog.getExistingDirectory(
        #path = getOpenFilesAndDirs(
            #parent=self,
            caption = "Select directory of sample named 'nxrefine'",
            directory = lastDirectory,
            options = QFileDialog.Option.DontUseNativeDialog,
            # filter = "Directory (*/nxrefine/)"
        )
        # self.pathSelected.emit(path)
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