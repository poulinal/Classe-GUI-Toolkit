# AP 2026
import sys
import os
import traceback

import matplotlib

matplotlib.use("Qt5Agg")

from CGTProject.pages.mainMenuPage import MainWindow
from CGTProject.notifications.dialog import show_crash_dialog
from CGTProject.utilities.memoryLogger import initialize_monitor, cleanup_monitor
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QCoreApplication, QTimer

QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)
QCoreApplication.setAttribute(Qt.AA_DisableHighDpiScaling)


def _configure_qt_for_x11_remote_rendering():
    """Use software rendering defaults to avoid black-window issues on XQuartz/X11 forwarding."""
    if not os.environ.get('DISPLAY'):
        return

    # os.environ.setdefault('QT_OPENGL', 'software')
    # os.environ.setdefault('QT_XCB_GL_INTEGRATION', 'none')
    # os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE', '1')
    # os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '0')

    # if hasattr(Qt, 'AA_UseSoftwareOpenGL'):
    #     QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
    # if hasattr(Qt, 'AA_DisableHighDpiScaling'):
    #     QCoreApplication.setAttribute(Qt.AA_DisableHighDpiScaling, True)

def main() -> int:
    _configure_qt_for_x11_remote_rendering()
    QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)

    # Initialize memory monitoring
    initialize_monitor(interval=5.0, memory_alert_threshold=0.9)
    
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        QTimer.singleShot(0, window.update)
        QTimer.singleShot(0, window.repaint)
        return app.exec_()
    except Exception:
        # Show fatal error details before terminating the app.
        error_message = traceback.format_exc()
        print(error_message)
        show_crash_dialog(error_message)
        return 1
    finally:
        # Cleanup monitoring on exit
        print("Cleaning up monitor")
        cleanup_monitor()


if __name__ == '__main__':
    sys.exit(main())