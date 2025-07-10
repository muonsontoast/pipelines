from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QPushButton, QCheckBox, QCompleter, QLineEdit,
    QSpacerItem, QMessageBox, QGridLayout, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPalette, QColor
from .settings import CreateSettingElement
from .scan import Scanner

class ControlPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.parent = window
        self.setLayout(QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.settings = dict()
        self.Push()

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings
    
    def Push(self):
        # Set the size
        size = self.settings.get('size', (None, None))
        sizePolicy = [None, None]
        # Set horizontal
        if size[0] is None:
            sizePolicy[0] = QSizePolicy.Expanding
        else:
            self.setFixedWidth(size[0])
            sizePolicy[0] = QSizePolicy.Preferred
        # Set vertical
        if size[1] is None:
            sizePolicy[1] = QSizePolicy.Expanding
        else:
            self.setFixedHeight(size[1])
            sizePolicy[1] = QSizePolicy.Preferred
        # Set size policy
        self.setSizePolicy(*sizePolicy)