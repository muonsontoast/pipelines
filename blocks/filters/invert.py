from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QSizePolicy, QGraphicsProxyWidget
from PySide6.QtCore import Qt
import numpy as np
from .filter import Filter
from ... import shared
from ... import style

class Invert(Filter):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            parent, 
            proxy,
            name = kwargs.pop('name', 'Invert (Filter)'),
            type = kwargs.pop('type', 'Invert'),
            size = kwargs.pop('size', [350, 150]),
            fontsize = kwargs.pop('fontsize', 12),
            **kwargs,
        )

    def Start(self):
        '''Returns NaN if there is signal in otherwise returns 1.'''
        if len(self.linksIn) > 0:
            ID = next(iter(self.linksIn))
            print(np.nan if not np.isnan(shared.entities[ID].data[1]) and shared.entities[ID].data[1] != 0 else 1)
            return np.nan if not np.isnan(shared.entities[ID].data[1]) and shared.entities[ID].data[1] != 0 else 1
        
    def Push(self):
        super().Push()
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(10, 10, 10, 20)
        btn = QPushButton('Push Me')
        btn.pressed.connect(self.Start)
        self.widget.layout().addWidget(btn, alignment = Qt.AlignCenter)
        self.main.layout().addWidget(self.widget)