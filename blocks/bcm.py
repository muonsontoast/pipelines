from PySide6.QtWidgets import QLabel, QGraphicsProxyWidget
from PySide6.QtCore import Qt
import numpy as np
from .pv import PV

class BCM(PV):
    '''Beam current monitor'''
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        self.typeLabel = QLabel('')
        self.typeLabel.setAlignment(Qt.AlignLeft)
        super().__init__(parent, proxy, name = kwargs.pop('name', 'BCM'), type = 'BCM', **kwargs)
        self.settings['components'].pop('value') # BCM is read-only.
        # Expose attributes from the underlying linked lattice element to the editor.
        self.linkedElementAttrs = {
            'charge': None,
            'numParticles': None,
            # can add more later.
        }
        # default stream 
        self.streams = {
            'beamCharge': lambda: { 
                'data': self.data,
            }
        }
        self.typeLabel.setText(self.type)
        self.UpdateColors()

    def Start(self, downstreamData:np.ndarray = None, **kwargs):
        if not self.online:
            # Only count the particles that are still alive in both x AND y
            xMask = np.isinf(downstreamData[0, :, self.settings['linkedElement'].Index])
            yMask = np.isinf(downstreamData[2, :, self.settings['linkedElement'].Index])
            finalMask = ~xMask & ~yMask # bitwise AND on the negated xMask and yMask, so only entries that are not NaN in both are recorded.
            self.data = finalMask.sum()

    def UpdateColors(self):
        pass