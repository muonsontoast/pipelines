from PySide6.QtWidgets import QFrame
from PySide6.QtCore import QSize

class Indicator(QFrame):
    def __init__(self, parent, radius):
        super().__init__()
        self.parent = parent
        self.diam = radius * 2
        self.setFixedSize(self.diam + 1, self.diam)
    
    def sizeHint(self):
        return QSize(self.diam, self.diam)