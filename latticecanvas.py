from PySide6.QtWidgets import QFrame, QVBoxLayout
from .canvas import Canvas

class LatticeCanvas(QFrame):
    def __init__(self, window):
        super().__init__()
        self.parent = window
        self.setLayout(QVBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.settings = dict()

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings