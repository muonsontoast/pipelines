from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget, QMenu
from PySide6.QtCore import Qt, QPointF
import numpy as np
from .filter import Filter
from ..draggable import Draggable
from ... import shared
from ..socket import Socket
from ... import style

class GreaterThan(Filter):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            parent, 
            proxy,
            name = kwargs.pop('name', 'Greater Than (Filter)'),
            type = kwargs.pop('type', 'Greater Than'),
            size = kwargs.pop('size', [350, 150]),
            fontsize = kwargs.pop('fontsize', 12),
            **kwargs,
        )
        self.threshold = 0
        
        btn = QPushButton('START')
        btn.setFixedSize(80, 30)
        self.main.layout().addWidget(btn, alignment = Qt.AlignCenter)
        btn.pressed.connect(self.Start)

    def Start(self):
        print('Starting!')
        if len(self.linksIn) > 0:
            ID = next(iter(self.linksIn))
            print('My value is', np.maximum(shared.entities[ID].data[1], self.threshold))
            return np.maximum(shared.entities[ID].data[1], self.threshold)