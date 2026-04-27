"""Style definitions for banner notifications."""

from enum import Enum
from PyQt5.QtGui import QColor


class NotificationStyle(Enum):
    """Enum for notification severity styles."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


# Color scheme for each style
STYLE_COLORS = {
    NotificationStyle.INFO: {
        'background': QColor(59, 130, 246),      # Blue
        'text': QColor(255, 255, 255),           # White
        'border': QColor(37, 99, 235),           # Darker blue
    },
    NotificationStyle.SUCCESS: {
        'background': QColor(34, 197, 94),       # Green
        'text': QColor(255, 255, 255),           # White
        'border': QColor(22, 163, 74),           # Darker green
    },
    NotificationStyle.WARNING: {
        'background': QColor(234, 179, 8),       # Amber
        'text': QColor(0, 0, 0),                 # Black
        'border': QColor(202, 138, 4),           # Darker amber
    },
    NotificationStyle.ERROR: {
        'background': QColor(239, 68, 68),       # Red
        'text': QColor(255, 255, 255),           # White
        'border': QColor(220, 38, 38),           # Darker red
    },
}


def get_stylesheet(style: NotificationStyle) -> str:
    """Generate stylesheet for a notification style."""
    colors = STYLE_COLORS[style]
    return f"""
        QWidget {{
            background-color: {colors['background'].name()};
            border: 2px solid {colors['border'].name()};
            border-radius: 8px;
            padding: 12px 16px;
        }}
        QLabel {{
            color: {colors['text'].name()};
            font-size: 14px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
    """
