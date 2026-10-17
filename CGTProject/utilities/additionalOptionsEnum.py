# AP 2026

from enum import Enum

class AdditionalOptionsEnum(Enum):
    """Enumeration for additional options in the GUI."""
    BLANK_STATE = "-- Select a Tool Option --"
    TRIM_DATA = "Trim Data"
    BIN_DATA = "Bin Data"
    SKEW_DATA = "Skew Data"
    CHANGE_COLORMAP = "Change Colormap"
    DOWNLOAD_DATA = "Download current data (.nxs)"
    
    def __str__(self):
        return self.value
    
    
    
    