"""Banner notification widget for displaying notifications."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QTimer, QPropertyAnimation, QRect, Qt
from PyQt5.QtGui import QFont

from .styles import NotificationStyle, get_stylesheet


class BannerNotification(QWidget):
    """
    A banner notification widget similar to macOS/iOS notifications.
    
    Features:
    - Auto-dismiss after configurable duration
    - Smooth slide-in/slide-out animations
    - Multiple severity styles (info, success, warning, error)
    - Optional close button
    """

    def __init__(
        self,
        message: str,
        parent=None,
        style: NotificationStyle = NotificationStyle.INFO,
        duration: int = 3000,
        icon: str = None,
    ):
        """
        Initialize a banner notification.
        
        Args:
            message: The notification message text
            parent: Parent widget
            style: NotificationStyle enum value (INFO, SUCCESS, WARNING, ERROR)
            duration: Duration to display in milliseconds (0 = no auto-dismiss)
            icon: Optional emoji or icon string to prepend to message
        """
        super().__init__(parent)
        self.style = style
        self.duration = duration
        self.is_closing = False

        # Setup UI
        self._setup_ui(message, icon)
        self._apply_styling()
        
        # Setup animation
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)  # 300ms animation
        
        # Setup auto-dismiss timer
        if duration > 0:
            self.dismiss_timer = QTimer()
            self.dismiss_timer.setSingleShot(True)
            self.dismiss_timer.timeout.connect(self.close_notification)
            self.dismiss_timer.start(duration)

    def _setup_ui(self, message: str, icon: str = None):
        """Setup the UI layout and widgets."""
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(0)
        
        # Create message label
        self.label = QLabel()
        font = QFont()
        font.setPointSize(8) #use styles.py to change font
        font.setFamily("-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif")
        self.label.setFont(font)
        self.label.setWordWrap(True)
        
        # Format message with icon if provided
        text = message
        if icon:
            text = f"{icon} {message}"
        
        self.label.setText(text)
        layout.addWidget(self.label)
        
        self.setLayout(layout)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setMaximumWidth(400)
        self.setMinimumHeight(50)

    def _apply_styling(self):
        """Apply stylesheet based on notification style."""
        self.setStyleSheet(get_stylesheet(self.style))

    def animate_in(self, start_pos: QRect, end_pos: QRect):
        """
        Animate the notification sliding in.
        
        Args:
            start_pos: Starting geometry (QRect)
            end_pos: Ending geometry (QRect)
        """
        self.setGeometry(start_pos)
        self.show()
        self.raise_()

        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()

    def close_notification(self):
        """Animate out and close the notification."""
        if self.is_closing:
            return
            
        self.is_closing = True
        
        # Stop the dismiss timer if it exists
        if hasattr(self, 'dismiss_timer'):
            self.dismiss_timer.stop()
        
        # Animate out
        current_geometry = self.geometry()
        end_geometry = QRect(
            current_geometry.x(),
            current_geometry.y() - current_geometry.height() - 10,
            current_geometry.width(),
            current_geometry.height()
        )
        
        self.animation.setStartValue(current_geometry)
        self.animation.setEndValue(end_geometry)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()

    def set_message(self, message: str):
        """Update the notification message."""
        self.label.setText(message)

    def extend_duration(self, additional_ms: int = None):
        """
        Extend the auto-dismiss timer.
        
        Args:
            additional_ms: Additional milliseconds to display
        """
        if hasattr(self, 'dismiss_timer') and self.dismiss_timer.isActive():
            if additional_ms:
                self.dismiss_timer.start(additional_ms)
            else:
                self.dismiss_timer.start(self.duration)
