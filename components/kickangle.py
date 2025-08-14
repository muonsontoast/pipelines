from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QSizePolicy
)
from . import slider
from .. import shared
from .. import style

class KickAngleComponent(QWidget):
    def __init__(self, pv, component):
        super().__init__()
        self.pv = pv
        self.component = component
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.slider = slider.SliderComponent(pv, component)
        self.layout().addWidget(self.slider)
        self.UpdateColors()

    def UpdateColors(self):
        pass