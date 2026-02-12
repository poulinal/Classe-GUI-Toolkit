# AP 2026
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

class ClasseDataModel:
    
    def __init__(self, dataPaths : tuple[str, list] = ("", [])):
        self.dic_temp_to_data : dict[str, NXdata] = {} # Temperature str to nxdata (HKL where H is nxaxes[0], K nxaxes[1], L nxaxes[2])
        self.dataPathRoot, self.dataMetadata = dataPaths
        self.index = 0
        self.temperature : str = ""
        self.HKLPlane : Optional[HKLPlaneEnum] = None
        
        self.initializeAllData()
        
    def setData(self, data):
        self.dic_temp_to_data = data
        
    def setIndex(self, index):
        self.index = index
        
    def getTemperatureValues(self):
        return list(self.dic_temp_to_data.keys())
        
    def setTemperature(self, temperatureValue : str):
        # Placeholder for setting temperature in the data model
        print(f"Setting temperature to: {temperatureValue}")
        if temperatureValue in self.getTemperatureValues():
            self.temperature = temperatureValue
        else:
            print(f"Temperature value {temperatureValue} not found in available values.")
            
    def getCurrentData(self) -> Optional[NXdata]:
        return self.dic_temp_to_data.get(self.temperature, None)
            
    def getHKLPlane(self) -> Optional[HKLPlaneEnum]:
        if self.HKLPlane is not None:
            return self.HKLPlane
        return None
            
    def setHKLPlane(self, hklPlaneStr : str):
        # Placeholder for setting HKL plane in the data model
        print(f"Setting HKL Plane to: {hklPlaneStr}")
        self.HKLPlane = HKLPlaneEnum.fromString(hklPlaneStr)
            
    def initializeAllData(self):
        # Placeholder for initializing all data from the provided paths
        print(f"Initializing data from root: {self.dataPathRoot}")
        print(f"Metadata files: {self.dataMetadata}")
        for metadata in self.dataMetadata:
            #temperature is between the _ and .nxs
            temp_value = metadata.split('_')[-1].split('.nxs')[0]
            print(f"Loading data for temperature: {temp_value} from metadata file: {metadata}")
            self.dic_temp_to_data[temp_value] = load_transform(metadata)
            
            print(f"zmax: {self.dic_temp_to_data[temp_value].nxaxes[0].max()}, shape: {self.dic_temp_to_data[temp_value].nxsignal.shape}") if self.dic_temp_to_data[temp_value] else print("No data loaded for this temperature.")
            
    def getMaxDepth(self) -> int:
        if self.temperature in self.dic_temp_to_data:
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
        print(f"Getting QuadMesh for temperature: {self.temperature} on plane: {self.HKLPlane}")
        axisToSlice = self.getSliceAxisIndex()
            
        z_axis_values = self.getCurrentData().nxaxes[axisToSlice]
        actual_value = z_axis_values[self.index]
        print(f"Getting QuadMesh at index: {self.index}, z_axis_values: {z_axis_values}, actual z value: {actual_value}")
        if self.getCurrentData() and self.index < len(z_axis_values) and self.temperature in self.dic_temp_to_data:
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
        if self.dic_temp_to_data and self.temperature in self.dic_temp_to_data:
            axis_values = self.getCurrentData().nxaxes[i]
            return (axis_values.min(), axis_values.max())
        return (0.0, 0.0)
    
    def getDataAxisResolution(self, i) -> float:
        """Get the resolution of the i'th axis
        
        Keyword arguments:
        argument -- description
        Return: return_description
        """
        if self.dic_temp_to_data and self.temperature in self.dic_temp_to_data:
            axis_values = self.getCurrentData().nxaxes[i]
            if len(axis_values) > 1:
                return axis_values[1] - axis_values[0]
        return 0.0
    
    def applyLineCutOptions(self, line_cut_options: dict[str, float], coords: tuple[float, float], verticle: bool):
        # Placeholder for applying line cut options to the data model
        print(f"Applying line cut options: {line_cut_options} at coords: {coords} verticle: {verticle}")
        if line_cut_options and self.temperature in self.dic_temp_to_data:
            if self.HKLPlane is None:
                print("HKL Plane not set. Cannot apply line cut options.")
                return
            elif self.HKLPlane == HKLPlaneEnum.H_K_Plane:
                hMin = line_cut_options.get('h_min', 0.0)
                hMax = line_cut_options.get('h_max', 0.0)
                kMin = line_cut_options.get('k_min', 0.0)
                kMax = line_cut_options.get('k_max', 0.0)
                lCenter = line_cut_options.get('l_center', 0.0)
                deltaL = line_cut_options.get('delta_l', 0.0)
            elif self.HKLPlane == HKLPlaneEnum.H_L_Plane:
                hMin = line_cut_options.get('h_min', 0.0)
                hMax = line_cut_options.get('h_max', 0.0)
                lMin = line_cut_options.get('l_min', 0.0)
                lMax = line_cut_options.get('l_max', 0.0)
                kCenter = line_cut_options.get('k_center', 0.0)
                deltaK = line_cut_options.get('delta_k', 0.0)
            elif self.HKLPlane == HKLPlaneEnum.K_L_Plane:
                kMin = line_cut_options.get('k_min', 0.0)
                kMax = line_cut_options.get('k_max', 0.0)
                lMin = line_cut_options.get('l_min', 0.0)
                lMax = line_cut_options.get('l_max', 0.0)
                hCenter = line_cut_options.get('h_center', 0.0)
                deltaH = line_cut_options.get('delta_h', 0.0)
                
        scissors = Scissors()
        scissors.set_data(self.dic_temp_to_data[self.temperature])
        # scissors.set_center((coords[0], coords[1], 0))  # Assuming the line cut is in the H-K plane for simplicity
        # scissors.set_window((hMin, hMax, kMin, kMax, lCenter - deltaL, lCenter + deltaL))  # Example window, adjust as needed
        scissors.set_center((0, 0, 0)) # Placeholder center, adjust based on HKL plane and coords
        scissors.set_window((0.1, 1, 0.2)) # Placeholder window, adjust based on HKL plane and line cut options
        extracted_data = scissors.cut_data()
        
        #and include graph options like cmap, vmin vmax colorramp, skewangle
        return extracted_data