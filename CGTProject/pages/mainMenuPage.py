# AP 2026

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QStackedWidget, QLabel)
from PyQt5.QtCore import Qt, QSettings
from CGTProject.pages.mainAnalysisPage import MainAnalysisPage
from CGTProject.pages.processDataPage import ProcessDataPage


class MainMenu(QWidget):
    """Main menu page with navigation buttons"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Main Menu")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title)
        
        # Menu buttons
        self.process_btn = QPushButton("Process Data")
        self.analyze_btn = QPushButton("Analyze Data")
        
        # Style buttons
        button_style = """
            QPushButton {
                padding: 15px;
                font-size: 16px;
                margin: 10px 50px;
            }
        """
        self.process_btn.setStyleSheet(button_style)
        self.analyze_btn.setStyleSheet(button_style)
        
        layout.addWidget(self.process_btn)
        layout.addWidget(self.analyze_btn)
        layout.addStretch()
        
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Application")
        self.setGeometry(100, 100, 600, 800)
        
        # Create stacked widget for page navigation
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        settings = QSettings('DeLTA', 'CGTProject')
        
        # Create pages
        self.main_menu = MainMenu()
        self.process_page = ProcessDataPage(settings)
        self.analyze_page = MainAnalysisPage(settings)
        
        # Add pages to stack
        self.stacked_widget.addWidget(self.main_menu)      # index 0
        self.stacked_widget.addWidget(self.process_page)   # index 1
        self.stacked_widget.addWidget(self.analyze_page)   # index 2
        
        # Connect navigation signals
        self.main_menu.process_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.main_menu.analyze_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        self.process_page.back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.analyze_page.back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
