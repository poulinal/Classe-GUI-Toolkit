# AP 2026

from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QApplication,
                             QPushButton, QStackedWidget, QLabel, QShortcut)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
from PyQt5.QtGui import QKeySequence
from CGTProject.pages.mainAnalysisPage import MainAnalysisPage
from CGTProject.pages.processDataPage import ProcessDataPage
from CGTProject.pages.lineCutPage import LineCutPage
from CGTProject.widgets.advancedTabWidget import AdvancedTabWidget
from CGTProject.pages.deltaPDFPage import DeltaPDFPage


class MainMenu(QWidget):
    """Main menu page with navigation buttons"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        self.tab_counter = 0
        
        # Title
        title = QLabel("Main Menu")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        layout.addWidget(title)
        
        # Menu buttons
        self.process_btn = QPushButton("Process Data")
        self.analyze_btn = QPushButton("Analyze Data (Scattering Datasets)")
        # self.deltaPDF_btn = QPushButton("Analyze Data (Diffuse Scattering Data)")
        
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
        # self.deltaPDF_btn.setStyleSheet(button_style)
        
        layout.addWidget(self.process_btn)
        layout.addWidget(self.analyze_btn)
        # layout.addWidget(self.deltaPDF_btn)
        layout.addStretch()
        
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Application")
        # self.setGeometry(100, 100, 600, 800)
        #set geometry to be 80% tall and 50% wide of the screen, and centered
        screen_geometry = QApplication.desktop().screenGeometry()
        width = screen_geometry.width() * 0.5
        height = screen_geometry.height() * 0.8
        x = (screen_geometry.width() - width) / 2
        y = (screen_geometry.height() - height) / 2
        self.setGeometry(int(x), int(y), int(width), int(height))
        
        # Create stacked widget for page navigation
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        settings = QSettings('DeLTA', 'CGTProject')
        
        # Create pages
        self.main_menu = MainMenu()
        self.process_page = ProcessDataPage(settings)
        self.analyze_page = MainAnalysisPage(settings)
        # self.deltapdf_page = DeltaPDFPage(settings)
        self.analyze_page.openExtractedData.connect(lambda extractedData: self.open_line_cut(extractedData))
        self.analyze_page.openDeltaPDF.connect(lambda dpdf: self.open_delta_pdf(settings, dpdf))
        
        # Create tab widget
        self.analysis_tab_widget = AdvancedTabWidget()
        # layout.addWidget(self.analysis_tab_widget)
        self.analysis_tab_widget.addTab(self.analyze_page, "Main Analysis Page")
        self.tab_counter = 1
        
        # TODO create tab widget for deltaPDF analysis and add deltapdf_page to it
        
        
        # Add pages to stack
        self.stacked_widget.addWidget(self.main_menu)      # index 0
        self.stacked_widget.addWidget(self.process_page)   # index 1
        self.stacked_widget.addWidget(self.analysis_tab_widget)   # index 2
        # self.stacked_widget.addWidget(self.deltapdf_page)   # index 3
        
        # Connect navigation signals
        self.main_menu.process_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.main_menu.analyze_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        # self.main_menu.deltaPDF_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        self.process_page.back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.analyze_page.back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        # self.deltapdf_page.back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        
    def setup_shortcuts(self):
        """Setup keyboard shortcuts for tab management"""
        
        # Ctrl+T to add new tab
        # new_tab_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        # new_tab_shortcut.activated.connect(self.add_new_tab)
        
        # Ctrl+W to close current tab
        close_tab_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_tab_shortcut.activated.connect(self.close_current_tab)
        
        # Ctrl+Shift+T to duplicate current tab
        duplicate_shortcut = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        duplicate_shortcut.activated.connect(self.duplicate_current_tab)
        
    
    def close_current_tab(self):
        current_index = self.analysis_tab_widget.currentIndex()
        self.analysis_tab_widget.close_tab(current_index)
    
    def duplicate_current_tab(self):
        current_index = self.analysis_tab_widget.currentIndex()
        self.analysis_tab_widget.duplicate_tab(current_index)
        
        
    def open_line_cut(self, extractedData):
        new_linecut_tab = LineCutPage(extractedData)
        
        tab_index = self.analysis_tab_widget.addTab(new_linecut_tab, f"LineCut Tab {self.tab_counter}")
        
        self.analysis_tab_widget.setCurrentIndex(tab_index)
        
        self.tab_counter += 1
        
    def open_delta_pdf(self, settings, dpdf):
        new_dpdf_tab = DeltaPDFPage(settings, dpdf)
        
        tab_index = self.analysis_tab_widget.addTab(new_dpdf_tab, f"DeltaPDF Tab {self.tab_counter}")
        
        self.analysis_tab_widget.setCurrentIndex(tab_index)
        
        self.tab_counter += 1