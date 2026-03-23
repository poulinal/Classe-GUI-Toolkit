# AP 2026
# interface for a broad classe data model which will be able to be used by classeDataModel and diffuseScatteringModel, and potentially other models in the future. This will allow for more modularity and flexibility in the codebase as we can have different data models for different types of data while still adhering to a common interface.

from abc import abstractmethod
from nxs_analysis_tools.datareduction import load_transform, plot_slice
from nxs_analysis_tools import Scissors
from matplotlib.collections import QuadMesh
from scipy.ndimage import map_coordinates
from typing import Optional

from CGTProject.utilities.HKLPlaneEnum import HKLPlaneEnum

# # Increase NX_MEMORY limit to handle large datasets (in MB)
# os.environ['NX_MEMORY'] = '8000'
from nexusformat.nexus import NXdata, nxsetmemory
nxsetmemory(80000)  # Set to 80000 MB or higher

class DataModel:
    
    def __init__(self):
        # self.dic_temp_to_data : dict[str, NXdata] = {} # Temperature str to nxdata (HKL where H is nxaxes[0], K nxaxes[1], L nxaxes[2])
        self.index = 0
        self.HKLPlane : Optional[HKLPlaneEnum] = None
        
        self.initializeAllData()
    
    @abstractmethod
    def setData(self, data):
        pass#self.dic_temp_to_data = data
        
    def setIndex(self, index):
        self.index = index
    
    @abstractmethod
    def getCurrentData(self) -> Optional[NXdata]:
        return None #self.dic_temp_to_data.get(self.temperature, None)
            
    def getHKLPlane(self) -> Optional[HKLPlaneEnum]:
        if self.HKLPlane is not None:
            return self.HKLPlane
        return None
            
    def setHKLPlane(self, hklPlaneStr : str):
        # Placeholder for setting HKL plane in the data model
        print(f"Setting HKL Plane to: {hklPlaneStr}")
        self.HKLPlane = HKLPlaneEnum.fromString(hklPlaneStr)
    
    @abstractmethod
    def initializeAllData(self):
        # Placeholder for initializing all data from the provided paths
        # print(f"Initializing data from root: {self.dataPathRoot}")
        # print(f"Metadata files: {self.dataMetadata}")
        # for metadata in self.dataMetadata:
        #     #temperature is between the _ and .nxs
        #     temp_value = metadata.split('_')[-1].split('.nxs')[0]
        #     print(f"Loading data for temperature: {temp_value} from metadata file: {metadata}")
        #     self.dic_temp_to_data[temp_value] = load_transform(metadata)
            
        print("No data loaded for this temperature.")
        
    @abstractmethod
    def dataIsValid(self):
        return True
            
    def getMaxDepth(self) -> int:
        if self.dataIsValid():
            if self.HKLPlane == HKLPlaneEnum.H_K_Plane:
                return len(self.getCurrentData().nxaxes[2]) - 1
            elif self.HKLPlane == HKLPlaneEnum.H_L_Plane:
                return len(self.getCurrentData().nxaxes[1]) - 1
            elif self.HKLPlane == HKLPlaneEnum.K_L_Plane:
                return len(self.getCurrentData().nxaxes[0]) - 1
        return 0
        
    def getQuadMeshAtCurrentIndex(self) -> QuadMesh:
        # Placeholder for extracting QuadMesh data at the current index
        if self.HKLPlane is None:
            print("HKL Plane not set.")
            return None
        # print(f"Getting QuadMesh for temperature: {self.temperature} on plane: {self.HKLPlane}")
        axisToSlice = self.getSliceAxisIndex()
            
        z_axis_values = self.getCurrentData().nxaxes[axisToSlice]
        actual_value = z_axis_values[self.index]
        print(f"Getting QuadMesh at index: {self.index}, z_axis_values: {z_axis_values}, actual z value: {actual_value}")
        if self.getCurrentData() and self.index < len(z_axis_values) and self.dataIsValid():
            #if self.HKLPlane == HKLPlaneEnum.H_K_Plane: plot_slice(self.data[self.temperature][:,:,self.index])
            if self.HKLPlane == HKLPlaneEnum.H_K_Plane:
                return plot_slice(self.getCurrentData()[:,:,self.index])
            elif self.HKLPlane == HKLPlaneEnum.H_L_Plane:
                return plot_slice(self.getCurrentData()[:,self.index,:])
            elif self.HKLPlane == HKLPlaneEnum.K_L_Plane:
                return plot_slice(self.getCurrentData()[self.index,:,:])
        else:
            print("No data available or temperature not found.")
        return None
    
    def getSliceAxisIndex(self) -> int:
        if self.HKLPlane == HKLPlaneEnum.H_K_Plane:
            return HKLPlaneEnum.toIndex(HKLPlaneEnum.K_L_Plane)
        elif self.HKLPlane == HKLPlaneEnum.H_L_Plane:
            return HKLPlaneEnum.toIndex(HKLPlaneEnum.H_K_Plane)
        elif self.HKLPlane == HKLPlaneEnum.K_L_Plane:
            return HKLPlaneEnum.toIndex(HKLPlaneEnum.H_L_Plane)
        return -1
    
    def getDataAxisMinMax(self, i) -> tuple[float, float]:
        """Get the min max of the i'th axis
        
        Keyword arguments:
        argument -- description
        Return: return_description
        """
        if self.dataIsValid():
            axis_values = self.getCurrentData().nxaxes[i]
            return (axis_values.min(), axis_values.max())
        return (0.0, 0.0)
    
    def getDataAxisResolution(self, i) -> float:
        """Get the resolution of the i'th axis
        
        Keyword arguments:
        argument -- description
        Return: return_description
        """
        if self.dataIsValid():
            axis_values = self.getCurrentData().nxaxes[i]
            if len(axis_values) > 1:
                return axis_values[1] - axis_values[0]
        return 0.0