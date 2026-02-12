# AP 2026

class LineCutModeEnum:
    HORIZONTAL = "Horizontal"
    VERTICAL = "Vertical"
    BOTH = "Vertical and Horizontal"
    
    @classmethod
    def list(cls):
        return [cls.HORIZONTAL, cls.VERTICAL, cls.BOTH]
    
    @classmethod
    def fromString(cls, modeStr: str):
        if modeStr == cls.HORIZONTAL:
            return cls.HORIZONTAL
        elif modeStr == cls.VERTICAL:
            return cls.VERTICAL
        elif modeStr == cls.BOTH:
            return cls.BOTH
        else:
            raise ValueError(f"Unknown Line Cut Mode: {modeStr}")