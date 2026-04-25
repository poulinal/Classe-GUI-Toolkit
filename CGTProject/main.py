# AP 2026
from CGTProject.pages.mainMenuPage import MainWindow
from CGTProject.utilities.memoryLogger import initialize_monitor, cleanup_monitor
from PyQt5.QtWidgets import QApplication
import sys

if __name__ == '__main__':
    # Initialize memory monitoring
    memory_monitor = initialize_monitor(interval=5.0, memory_alert_threshold=0.9)
    
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    finally:
        # Cleanup monitoring on exit
        print("Cleaning up monitor")
        cleanup_monitor()