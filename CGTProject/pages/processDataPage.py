# AP 2026
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt, QSettings

class ProcessDataPage(QWidget):
    """Process Data page"""
    def __init__(self, settings : QSettings):
        super().__init__()
        layout = QVBoxLayout()
        
        self.settings = settings
        
        title = QLabel("Process Data")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin: 20px;")
        
        self.back_btn = QPushButton("← Back to Main Menu")
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.back_btn)
        
        self.setLayout(layout)