# AP 2026
# extension of dataModel, meant for temperature dependent scattering data
from nxs_analysis_tools.datareduction import load_transform, plot_slice
from nxs_analysis_tools import Scissors
from matplotlib.collections import QuadMesh
from scipy.ndimage import map_coordinates
from typing import Optional

from CGTProject.utilities.HKLPlaneEnum import HKLPlaneEnum
from CGTProject.models.dataModel import DataModel

# # Increase NX_MEMORY limit to handle large datasets (in MB)
# os.environ['NX_MEMORY'] = '8000'
from nexusformat.nexus import NXdata, nxsetmemory
nxsetmemory(80000)  # Set to 80000 MB or higher

class TemperatureDataModel(DataModel):
    
    def __init__(self, dataPaths : tuple[str, list] = ("", [])):
        self.dic_temp_to_data : dict[str, NXdata] = {} # Temperature str to nxdata (HKL where H is nxaxes[0], K nxaxes[1], L nxaxes[2])
        self.temperature : str = ""
        super().__init__(dataPaths)
        
        
    def setData(self, data):
        self.dic_temp_to_data = data
        
    def dataIsValid(self):
        return self.dic_temp_to_data and self.temperature in self.dic_temp_to_data and self.getCurrentData() is not None
    
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
            
    
    def applyLineCutOptions(self, line_cut_options: dict[str, float], coords: tuple[float, float], verticle: bool):
        # Placeholder for applying line cut options to the data model
        print(f"Applying line cut options: {line_cut_options} at coords: {coords} verticle: {verticle}")
        scissors = Scissors()
        scissors.set_data(self.dic_temp_to_data[self.temperature])
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
                h_half = (hMax - hMin) / 2
                k_half = (kMax - kMin) / 2
                l_half = deltaL / 2
                scissors.set_center((coords[0], coords[1], lCenter))  # Assuming the line cut is in the H-K plane for simplicity
                scissors.set_window((h_half, k_half, l_half))
            elif self.HKLPlane == HKLPlaneEnum.H_L_Plane:
                hMin = line_cut_options.get('h_min', 0.0)
                hMax = line_cut_options.get('h_max', 0.0)
                lMin = line_cut_options.get('l_min', 0.0)
                lMax = line_cut_options.get('l_max', 0.0)
                kCenter = line_cut_options.get('k_center', 0.0)
                deltaK = line_cut_options.get('delta_k', 0.0)
                h_half = (hMax - hMin) / 2
                l_half = (lMax - lMin) / 2
                k_half = deltaK / 2
                scissors.set_center((coords[0], kCenter, coords[1]))  # Assuming the line cut is in the H-L plane for simplicity
                scissors.set_window((h_half, k_half, l_half))  # Example window, adjust as needed
            elif self.HKLPlane == HKLPlaneEnum.K_L_Plane:
                kMin = line_cut_options.get('k_min', 0.0)
                kMax = line_cut_options.get('k_max', 0.0)
                lMin = line_cut_options.get('l_min', 0.0)
                lMax = line_cut_options.get('l_max', 0.0)
                hCenter = line_cut_options.get('h_center', 0.0)
                deltaH = line_cut_options.get('delta_h', 0.0)
                k_half = (kMax - kMin) / 2
                l_half = (lMax - lMin) / 2
                h_half = deltaH / 2
                scissors.set_center((hCenter, coords[0], coords[1]))  # Assuming the line cut is in the K-L plane for simplicity
                scissors.set_window((h_half, k_half, l_half))  # Example window, adjust as needed
                
        # scissors.set_center((coords[0], coords[1], 0))  # Assuming the line cut is in the H-K plane for simplicity
        # scissors.set_window((hMin, hMax, kMin, kMax, lCenter - deltaL, lCenter + deltaL))  # Example window, adjust as needed
        # scissors.set_center((0, 0, 0)) # Placeholder center, adjust based on HKL plane and coords
        # scissors.set_window((0.1, 1, 0.2)) # Placeholder window, adjust based on HKL plane and line cut options
        extracted_data = scissors.cut_data()
        
        #and include graph options like cmap, vmin vmax colorramp, skewangle
        return extracted_data