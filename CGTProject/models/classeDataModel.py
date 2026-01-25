# AP 2026
import os
from nexusformat.nexus import NXdata
from nxs_analysis_tools.datareduction import load_transform, plot_slice
from matplotlib.collections import QuadMesh

# # Increase NX_MEMORY limit to handle large datasets (in MB)
# os.environ['NX_MEMORY'] = '8000'
from nexusformat.nexus import nxsetmemory
nxsetmemory(80000)  # Set to 80000 MB or higher

class ClasseDataModel:
    
    def __init__(self, dataPaths : tuple[str, list] = ("", [])):
        self.data : dict[str, NXdata] = {}
        self.dataPathRoot, self.dataMetadata = dataPaths
        self.index = 0
        self.temperature : str = ""
        
        self.initializeAllData()
        
    def setData(self, data):
        self.data = data
        
    def setIndex(self, index):
        self.index = index
        
    def getTemperatureValues(self):
        return list(self.data.keys())
        
    def setTemperature(self, temperatureValue : str):
        # Placeholder for setting temperature in the data model
        print(f"Setting temperature to: {temperatureValue}")
        if temperatureValue in self.getTemperatureValues():
            self.temperature = temperatureValue
        else:
            print(f"Temperature value {temperatureValue} not found in available values.")
            
    def initializeAllData(self):
        # Placeholder for initializing all data from the provided paths
        print(f"Initializing data from root: {self.dataPathRoot}")
        print(f"Metadata files: {self.dataMetadata}")
        for metadata in self.dataMetadata:
            #temperature is between the _ and .nxs
            temp_value = metadata.split('_')[-1].split('.nxs')[0]
            print(f"Loading data for temperature: {temp_value} from metadata file: {metadata}")
            self.data[temp_value] = load_transform(metadata)
            
            print(f"zmax: {self.data[temp_value].nxaxes[0].max()}, shape: {self.data[temp_value].nxsignal.shape}")
        
    def getQuadMeshAtCurrentIndex(self) -> QuadMesh:
        # Placeholder for extracting QuadMesh data at the current index
        z_axis_values = self.data[self.temperature].nxaxes[2]
        actual_value = z_axis_values[self.index]
        print(f"Getting QuadMesh at index: {self.index}, z_axis_values: {z_axis_values}, actual z value: {actual_value}")
        if self.data and self.index < len(z_axis_values) and self.temperature in self.data:
            return plot_slice(self.data[self.temperature][:,:,self.index])
        else:
            print("No data available or temperature not found.")
        return None