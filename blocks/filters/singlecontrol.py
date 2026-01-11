from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget
from PySide6.QtCore import Qt
import numpy as np
from .filter import Filter
from ... import shared
from ... import style

class SingleControl(Filter):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            parent, 
            proxy,
            name = kwargs.pop('name', 'Single Control (Filter)'),
            type = kwargs.pop('type', 'Single Control'),
            size = kwargs.pop('size', [385, 250]),
            fontsize = kwargs.pop('fontsize', 12),
            threshold = kwargs.pop('threshold', 0),
            **kwargs,
        )

    def Start(self):
        print('Starting!')
        count = 0
        inID = None
        controlID = None
        for ID, socket in self.linksIn.items():
            count += 1
            if socket == 'in':
                inID = ID
            else:
                controlID = ID
        print('count is', count)
        print('inID:', inID)
        if count < 2 or inID == None:
            return np.nan
        # returns nan if the control is not supplying a number otherwise, returns the input data.
        print('outputting:', shared.entities[inID].data[1] if not isinstance(shared.entities[controlID].data[1], np.nan) else np.nan)
        return shared.entities[inID].data[1] if not isinstance(shared.entities[controlID].data[1], np.nan) else np.nan
        
    def Push(self):
        super().Push()
        self.AddSocket('control', 'F', 'Control', 135, acceptableTypes = ['PV', 'Corrector', 'BPM', 'Guassian Process', 'Less Than', 'Greater Than', 'Single Control'])
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(10, 10, 10, 20)
        btn = QPushButton('Push Me!')
        btn.pressed.connect(self.Start)
        self.widget.layout().addWidget(btn)
        self.main.layout().addWidget(self.widget)
        self.BaseStyling()