from PySide6.QtWidgets import QWidget
from .. import shared

class Component(QWidget):
    def __init__(self, pv, component, expandable = None, **kwargs):
        super().__init__()
        self.pv = pv
        self.component = component
        self.expandable = expandable