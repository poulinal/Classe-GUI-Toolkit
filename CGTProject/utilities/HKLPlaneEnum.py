# AP 2026

class HKLPlaneEnum:
    H_K_Plane = "H-K Plane" # corresponds to 0
    H_L_Plane = "H-L Plane" # corresponds to 1
    K_L_Plane = "K-L Plane" # corresponds to 2
    
    @classmethod
    def list(cls):
        return [cls.H_K_Plane, cls.H_L_Plane, cls.K_L_Plane]
    @classmethod
    def fromString(cls, planeStr: str) -> str:
        if planeStr == cls.H_K_Plane:
            return cls.H_K_Plane
        elif planeStr == cls.H_L_Plane:
            return cls.H_L_Plane
        elif planeStr == cls.K_L_Plane:
            return cls.K_L_Plane
        else:
            raise ValueError(f"Unknown HKL Plane: {planeStr}")
        
    @classmethod
    def toIndex(cls, planeStr: str) -> int:
        if planeStr == cls.H_K_Plane:
            return 0
        elif planeStr == cls.H_L_Plane:
            return 1
        elif planeStr == cls.K_L_Plane:
            return 2
        else:
            raise ValueError(f"Unknown HKL Plane: {planeStr}")
        