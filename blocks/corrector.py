from PySide6.QtWidgets import QLabel, QGraphicsProxyWidget
from PySide6.QtCore import Qt
from multiprocessing.shared_memory import SharedMemory
import numpy as np
from .pv import PV
from ..components import kickangle
from .. import shared
from .. import style
from ..utils import cothread

class Corrector(PV):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''`alignment` = <Horizontal/Vertical>\n
        `size` = ( x , y )'''
        # Type and Alignment
        self.typeLabel = QLabel()
        self.typeLabel.setAlignment(Qt.AlignLeft)
        # invoke parent pv constructor
        super().__init__(parent, proxy, name = kwargs.pop('name', 'Corrector'), type = 'Corrector', **kwargs)
        self.settings['alignment'] = kwargs.get('alignment', 'Vertical')
        self.settings['components']['value'] = dict(name = 'Kick', value = 0, min = 0, max = 100, default = 0, units = 'mrad', type = kickangle.KickAngleComponent)
        # override default stream
        self.streams['default'] = lambda: {
            'data': self.data,
            'default': self.settings['components']['value']['default'],
            'lims': [self.settings['components']['value']['min'], self.settings['components']['value']['max']],
            'alignments': self.settings['alignment'],
            'linkedIdx': self.settings['linkedElement'].Index if 'linkedElement' in self.settings else None,
            'plottype': 'plot',
            'xunits': '',
            'yunits': '',
        }
        # Add labels to layout
        self.typeLabel.setText(f'{self.type} ({self.settings['alignment']})')
        # Apply colors
        self.UpdateColors()

    def Start(self, setpoint: int|float = None, **kwargs):
        if not hasattr(self, 'sharedMemory'):
            self.sharedMemory = SharedMemory(name = self.dataSharedMemoryName)
            self.data = np.ndarray(self.dataSharedMemoryShape, self.dataSharedMemoryDType, buffer = self.sharedMemory.buf)
        self.data[:] = np.inf
        child = kwargs.get('child', None)
        if child is None or (child is not None and not child.online):
            if setpoint is not None:
                self.UpdateLinkedElement(override = setpoint)
                self.settings['components']['value']['value'] = float(setpoint)
                self.data[0] = setpoint
            else:
                self.data[0] = self.settings['components']['value']['value']

    def UpdateColors(self):
        super().UpdateColors()
        if shared.lightModeOn:
            self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#1e1e1e", textAlign = 'left', padding = 0))
        else:
            self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#c4c4c4", textAlign = 'left', padding = 0))