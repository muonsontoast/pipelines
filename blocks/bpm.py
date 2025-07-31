from PySide6.QtWidgets import QLabel, QSizePolicy, QSpacerItem, QGraphicsProxyWidget
from PySide6.QtCore import Qt
from .pv import PV
from ..components import kickangle
from .. import shared
from .. import style

class BPM(PV):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''`alignment` = <Horizontal/Vertical> (str)'''
        # Type and Alignment
        self.typeLabel = QLabel('')
        self.typeLabel.setAlignment(Qt.AlignLeft)
        super().__init__(parent, proxy, name = kwargs.pop('name', 'BPM'), type = kwargs.pop('type', BPM), size = kwargs.pop('size', (225, 50)), **kwargs)
        self.blockType = 'BPM'
        self.settings['alignment'] = kwargs.get('alignment', 'Vertical')
        self.settings['components'].pop('value') # BPM is read-only.
        # Add labels to layout
        self.widget.layout().addWidget(self.typeLabel, 1, 1, alignment = Qt.AlignLeft)
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Preferred, QSizePolicy.Expanding))
        self.typeLabel.setText(f'~ BPM ({self.settings['alignment']})')
        # Apply colors
        self.UpdateColors()

    def UpdateColors(self):
        super().UpdateColors()
        if shared.lightModeOn:
            self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#1e1e1e", textAlign = 'left', padding = 0))
        else:
            self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#c4c4c4", textAlign = 'left', padding = 0))

    # def UpdateColors(self):
    #     # if shared.lightModeOn:
    #     #     self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#1e1e1e", textAlign = 'left', padding = 0))
    #     # else:
    #     #     self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#c4c4c4", textAlign = 'left', padding = 0))
    #     pass

    # def BaseStyling(self):
    #     if shared.lightModeOn:
    #         return
    #     self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 4))
    #     self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#c4c4c4", textAlign = 'left', padding = 0))

    # def SelectedStyling(self):
    #     if shared.lightModeOn:
    #         return
    #     self.widget.setStyleSheet(style.WidgetStyle(color = '#3e3e3e', borderRadius = 4))
    #     self.typeLabel.setStyleSheet(style.LabelStyle(fontColor = "#c4c4c4", textAlign = 'left', padding = 0))