from PySide6.QtWidgets import QFrame
from PySide6.QtCore import QSize
from . import style

class Indicator(QFrame):
    def __init__(self, window, radius):
        super().__init__()
        self.parent = window
        self.diam = radius * 2
        self.setFixedSize(self.diam, self.diam)
        self.setStyleSheet(style.indicatorStyle(radius))
    
    def sizeHint(self):
        return QSize(self.diam, self.diam)