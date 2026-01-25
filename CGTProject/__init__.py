"""
Classe-GUI-Toolkit
================
A Python package for providing an efficient workflow for analyzing Cornell CLASSE data
"""

__version__ = "0.1.0"
__author__ = "Alexander Poulin"
__email__ = ""

# Package-level imports can be added here
from .utilities import *
from .widgets import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from .pages import *
from .models import *