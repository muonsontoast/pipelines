from PySide6.QtWidgets import QLabel, QSizePolicy, QSpacerItem, QGraphicsProxyWidget
from PySide6.QtCore import Qt
from .pv import PV
from ..components import kickangle
from .. import shared
from .. import style

class Corrector(PV):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''`alignment` = <Horizontal/Vertical>\n
        `size` = ( x , y )'''
        # Type and Alignment
        self.typeLabel = QLabel()
        self.typeLabel.setAlignment(Qt.AlignLeft)
        # invoke parent pv constructor
        super().__init__(parent, proxy, name = kwargs.pop('name', 'Corrector'), type = 'Corrector', size = kwargs.pop('size', [225, 50]))
        self.blockType = 'Corrector'
        self.settings['alignment'] = kwargs.get('alignment', 'Vertical')
        self.settings['components']['value'] = dict(name = 'Slider', value = 0, min = 0, max = 100, default = 0, units = 'mrad', type = kickangle.KickAngleComponent)
        # Add labels to layout
        self.widget.layout().addWidget(self.typeLabel, 1, 1, alignment = Qt.AlignLeft)
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Preferred, QSizePolicy.Expanding))
        self.typeLabel.setText(f'{self.type} ({self.settings['alignment']})')
        # Apply colors
        self.UpdateColors()

    def UpdateColors(self):
        super().UpdateColors()
        if shared.lightModeOn:
            self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#1e1e1e", textAlign = 'left', padding = 0))
        else:
            self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#c4c4c4", textAlign = 'left', padding = 0))