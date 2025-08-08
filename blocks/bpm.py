from PySide6.QtWidgets import QLabel, QGraphicsProxyWidget
from PySide6.QtCore import Qt
from .pv import PV

class BPM(PV):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''`alignment` = <Horizontal/Vertical> (str)'''
        self.typeLabel = QLabel('')
        self.typeLabel.setAlignment(Qt.AlignLeft)
        super().__init__(parent, proxy, name = kwargs.pop('name', 'BPM'), type = 'BPM')
        self.settings['alignment'] = kwargs.get('alignment', 'Vertical')
        self.settings['components'].pop('value') # BPM is read-only.
        # Expose attributes from the underlying linked lattice element to the editor.
        self.linkedElementAttrs = {
            'centroid': None,
            'portait': None,
            'numParticles': None,
            # can add more later.
        }
        self.typeLabel.setText(f'{self.type} ({self.settings['alignment']})')
        self.UpdateColors()

    def UpdateColors(self):
        pass