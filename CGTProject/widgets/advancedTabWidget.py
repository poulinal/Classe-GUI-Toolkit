# 2026 ADP
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                            QVBoxLayout, QPushButton, QLabel, QMessageBox, QMenu)
from PyQt5.QtCore import Qt

class AdvancedTabWidget(QTabWidget):
    """Extended tab widget with additional closing features"""
    def __init__(self):
        super().__init__()
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.setMovable(True)  # Allow tab reordering
        
        # Enable context menu for tabs
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def close_tab(self, index):
        """Close tab with optional confirmation"""
        if index == 0:  # Protect main tab
            return
        
        widget = self.widget(index)
        self.removeTab(index)
        if widget:
            widget.deleteLater()
    
    def show_context_menu(self, position):
        """Show right-click context menu on tabs"""
        tab_index = self.tabBar().tabAt(position)
        if tab_index == -1:
            return
        
        menu = QMenu(self)
        
        if tab_index != 0:  # Don't show close options for main tab
            close_action = menu.addAction("Close Tab")
            close_action.triggered.connect(lambda: self.close_tab(tab_index))
            
            close_others_action = menu.addAction("Close Other Tabs")
            close_others_action.triggered.connect(lambda: self.close_other_tabs(tab_index))
            
            close_right_action = menu.addAction("Close Tabs to the Right")
            close_right_action.triggered.connect(lambda: self.close_tabs_to_right(tab_index))
        
        duplicate_action = menu.addAction("Duplicate Tab")
        duplicate_action.triggered.connect(lambda: self.duplicate_tab(tab_index))
        
        menu.exec(self.mapToGlobal(position))
    
    def close_other_tabs(self, keep_index):
        """Close all tabs except the specified one and main tab"""
        # Close from right to left to maintain indices
        for i in range(self.count() - 1, 0, -1):
            if i != keep_index:
                self.close_tab(i)
    
    def close_tabs_to_right(self, from_index):
        """Close all tabs to the right of specified index"""
        for i in range(self.count() - 1, from_index, -1):
            self.close_tab(i)
    
    def duplicate_tab(self, index):
        """Duplicate the specified tab"""
        if index == 0:
            # For main tab, just add a new regular tab
            new_content = TabContent(self.count())
            self.addTab(new_content, f"Tab {self.count()}")
        else:
            # For other tabs, create a copy
            original_widget = self.widget(index)
            if hasattr(original_widget, 'tab_number'):
                new_content = TabContent(self.count())
                new_index = self.addTab(new_content, f"Copy of {self.tabText(index)}")
                self.setCurrentIndex(new_index)
    
    # def setup_shortcuts(self):
    #     """Setup keyboard shortcuts for tab management"""
    #     from PyQt6.QtGui import QShortcut, QKeySequence
        
    #     # Ctrl+T to add new tab
    #     new_tab_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
    #     new_tab_shortcut.activated.connect(self.add_new_tab)
        
    #     # Ctrl+W to close current tab
    #     close_tab_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
    #     close_tab_shortcut.activated.connect(self.close_current_tab)
        
    #     # Ctrl+Shift+T to duplicate current tab
    #     duplicate_shortcut = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
    #     duplicate_shortcut.activated.connect(self.duplicate_current_tab)
    

class TabContent(QWidget):
    """Content class for each tab"""
    def __init__(self, tab_number):
        super().__init__()
        self.tab_number = tab_number
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Add some content to demonstrate the tab
        label = QLabel(f"This is Tab {self.tab_number}")
        button = QPushButton(f"Button in Tab {self.tab_number}")
        button.clicked.connect(lambda: print(f"Button clicked in tab {self.tab_number}"))
        
        layout.addWidget(label)
        layout.addWidget(button)
        self.setLayout(layout)