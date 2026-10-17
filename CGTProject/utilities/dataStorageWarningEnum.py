#AP 2026

class DataStorageWarningEnum:
    """
    Enum class that details the different levels of warning for data storage usage (in bytes).
    Values:
        WARNING: 1 GB
        CRITICAL: 10 GB
    """
    
    WARNING = 1 * 1e9 # 1 GB
    CRITICAL = 10 * 1e9 # 10 GB
    
    # WARNING = 15 * 1e6 # 15 MB
    # CRITICAL = 100 * 1e6 # 100 MB
    
    def get_warning_level(data_storage_usage):
        """
        Returns the warning level based on the data storage usage.
        
        Parameters:
            data_storage_usage (float): The data storage usage in bytes.
        
        Returns:
            str: The warning level ('Normal', 'Warning', 'Critical').
        """
        if data_storage_usage >= DataStorageWarningEnum.CRITICAL:
            return 'Critical'
        elif data_storage_usage >= DataStorageWarningEnum.WARNING:
            return 'Warning'
        else:
            return 'Normal'
        
        