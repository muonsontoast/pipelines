'''
For read-only PVs like BPMs where only a single read-only numerical field should be shown.
'''

from PySide6.QtWidgets import (
    QWidget, QLineEdit, QSlider, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from .. import shared
from .. import style

class ValueComponent(QWidget):
    def __init__(self, pv, component, floatdp = 3, **kwargs):
        '''Leave `sliderSteps` at 1e6 for smooth sliding, or restrict to a low number for discrete applications.\n
        `floatdp` is the decimal precision of the line edit elements.\n
        `paddingLeft` and `paddingBottom` (int) are padding for text inside line edit elements.'''
        super().__init__()
        self.paddingLeft = kwargs.get('paddingLeft', 5)
        self.paddingBottom = kwargs.get('paddingBottom', 5)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(10, 0, 0, 15)
        self.layout().setSpacing(10)
        self.setFixedHeight(100)
        self.pv = pv
        self.component = component
        self.floatdp = int(floatdp)
        # Value
        self.value = QLineEdit(f'{pv.settings['components'][component]['value']:.{self.floatdp}f}')
        self.value.setAlignment(Qt.AlignCenter)
        self.value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.value.setReadOnly(True)
        # Hint text
        self.text = QLabel(f'This PV cannot be written to.')
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Add elements
        self.layout().addWidget(self.value)
        self.layout().addWidget(self.text)
        # Apply colors
        self.UpdateColors()

    def UpdateColors(self, **kwargs):
        '''Override `fillColorLight` and `fillColorDark` with a #ABCDEF color string.'''
        fillColorDark = kwargs.get('fillColorDark', "#4E4E4E")
        fillColorLight = kwargs.get('fillColorLight', "#AFAFAF")
        if shared.lightModeOn:
            self.value.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))
            return
        self.value.setStyleSheet(style.LineEditStyle(color = '#222222', bold = True, fontColor = '#c4c4c4', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))