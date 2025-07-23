from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QHBoxLayout, QSizePolicy, QSpacerItem, QGraphicsLineItem, QGraphicsProxyWidget
from PySide6.QtCore import Qt
from .pv import PV
from .. import shared
from .. import style

class Kicker(PV):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, name, size = (225, 50), alignment = 'Vertical'):
        '''`alignment` = <Horizontal/Vertical> (str)'''
        # Type and Alignment
        self.typeLabel = QLabel('')
        self.typeLabel.setAlignment(Qt.AlignLeft)
        # invoke parent pv constructor
        super().__init__(parent, proxy, name, size)
        # Add labels to layout
        self.widget.layout().addWidget(self.typeLabel, 1, 1, alignment = Qt.AlignLeft)
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Preferred, QSizePolicy.Expanding))
        self.settings['alignment'] = alignment
        self.typeLabel.setText(f'~ Kicker ({self.settings['alignment']})')
        # Apply colors
        self.UpdateColors()

    def UpdateColors(self):
        super().UpdateColors()
        if shared.lightModeOn:
            self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#1e1e1e", textAlign = 'left', padding = 0))
        else:
            self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#c4c4c4", textAlign = 'left', padding = 0))