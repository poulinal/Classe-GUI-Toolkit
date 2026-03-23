# AP 2026
#extension of dataModel, meant for diffuse scattering data (without temperature?)
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

class DiffuseDataModel(DataModel):
    def __init__(self, dpdf):
        # self.dic_temp_to_data : dict[str, NXdata] = {} # Temperature str to nxdata (HKL where H is nxaxes[0], K nxaxes[1], L nxaxes[2])
        super().__init__()
        self.dpdf = dpdf
        self.HKLPlane = HKLPlaneEnum.H_K_Plane
        
    def getCurrentData(self) -> Optional[NXdata]:
        return self.dpdf.fft #self.dic_temp_to_data.get(self.temperature, None)
    
    # self.page_title.setText("Delta PDF Analysis")
        # plot_slice(dpdf.fft[:,:,0.0]/1e3, cmap='seismic',
        #    vmin=-5, vmax=5,
        #    xlim=(-3,3),
        #    ylim=(-3,3),
        #   )