"""Manager for handling multiple banner notifications."""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QRect, Qt

from .banner import BannerNotification
from .styles import NotificationStyle


class BannerManager:
    """
    Manages banner notifications, handling positioning and lifecycle.
    
    Features:
    - Automatically positions notifications
    - Stacks multiple notifications
    - Handles notification cleanup
    - Configurable positioning (top-center, top-right, etc.)
    """

    # Position constants
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    TOP_LEFT = "top_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM_LEFT = "bottom_left"

    def __init__(
        self,
        parent_widget: QWidget,
        position: str = TOP_CENTER,
        offset_x: int = 0,
        offset_y: int = 20,
    ):
        """
        Initialize the banner manager.
        
        Args:
            parent_widget: The parent widget (usually the main window)
            position: Position preset (TOP_CENTER, TOP_RIGHT, etc.)
            offset_x: Horizontal offset from position in pixels
            offset_y: Vertical offset between notifications in pixels
        """
        self.parent_widget = parent_widget
        self.position = position
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.active_notifications = []

    def show_notification(
        self,
        message: str,
        style: NotificationStyle = NotificationStyle.INFO,
        duration: int = 3000,
        icon: str = None,
    ) -> BannerNotification:
        """
        Show a banner notification.
        
        Args:
            message: Notification message text
            style: NotificationStyle enum value
            duration: Duration in milliseconds (0 = no auto-dismiss)
            icon: Optional emoji/icon to display
            
        Returns:
            The created BannerNotification widget
        """
        notification = BannerNotification(
            message=message,
            parent=self.parent_widget,
            style=style,
            duration=duration,
            icon=icon,
        )
        
        # Position the notification
        start_pos = self._calculate_start_position(notification)
        end_pos = self._calculate_end_position(notification)
        
        # Connect cleanup signal
        notification.destroyed.connect(lambda: self._remove_notification(notification))
        
        # Animate in
        notification.animate_in(start_pos, end_pos)
        self.active_notifications.append(notification)
        
        return notification

    def show_info(self, message: str, duration: int = 3000, icon: str = "ℹ️"):
        """Show an info notification."""
        return self.show_notification(message, NotificationStyle.INFO, duration, icon)

    def show_success(self, message: str, duration: int = 3000, icon: str = "✓"):
        """Show a success notification."""
        return self.show_notification(message, NotificationStyle.SUCCESS, duration, icon)

    def show_warning(self, message: str, duration: int = 3000, icon: str = "⚠️"):
        """Show a warning notification."""
        return self.show_notification(message, NotificationStyle.WARNING, duration, icon)

    def show_error(self, message: str, duration: int = 3000, icon: str = "✕"):
        """Show an error notification."""
        return self.show_notification(message, NotificationStyle.ERROR, duration, icon)

    def _calculate_start_position(self, notification: BannerNotification) -> QRect:
        """Calculate the starting position (off-screen) for a notification."""
        notification.adjustSize()
        width = notification.width()
        height = notification.height()
        
        parent_rect = self.parent_widget.rect()
        parent_global = self.parent_widget.mapToGlobal(parent_rect.topLeft())
        
        # Determine horizontal position
        if "center" in self.position:
            x = parent_global.x() + (parent_rect.width() - width) // 2
        elif "right" in self.position:
            x = parent_global.x() + parent_rect.width() - width - 20
        else:  # left
            x = parent_global.x() + 20
        
        # Start off-screen at the top
        y = parent_global.y() - height - 10
        
        return QRect(x, y, width, height)

    def _calculate_end_position(self, notification: BannerNotification) -> QRect:
        """Calculate the ending position for a notification."""
        notification.adjustSize()
        width = notification.width()
        height = notification.height()
        
        parent_rect = self.parent_widget.rect()
        parent_global = self.parent_widget.mapToGlobal(parent_rect.topLeft())
        
        # Determine horizontal position
        if "center" in self.position:
            x = parent_global.x() + (parent_rect.width() - width) // 2
        elif "right" in self.position:
            x = parent_global.x() + parent_rect.width() - width - 20
        else:  # left
            x = parent_global.x() + 20
        
        # Stack notifications vertically
        num_active = len(self.active_notifications)
        
        if "bottom" in self.position:
            y = parent_global.y() + parent_rect.height() - height - 20 - (num_active * (height + self.offset_y))
        else:  # top
            y = parent_global.y() + 20 + (num_active * (height + self.offset_y))
        
        return QRect(x, y, width, height)

    def _remove_notification(self, notification: BannerNotification):
        """Remove a notification from the active list."""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
            # Reposition remaining notifications
            self._reposition_notifications()

    def _reposition_notifications(self):
        """Reposition all active notifications after one is removed."""
        for i, notification in enumerate(self.active_notifications):
            # Animate to new position
            new_pos = self._calculate_end_position(notification)
            notification.animation.setStartValue(notification.geometry())
            notification.animation.setEndValue(new_pos)
            notification.animation.start()

    def clear_all(self):
        """Close all active notifications."""
        for notification in list(self.active_notifications):
            notification.close_notification()

    def get_active_count(self) -> int:
        """Return the number of active notifications."""
        return len(self.active_notifications)
