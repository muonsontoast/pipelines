from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QSizePolicy
)
from . import slider
from .. import shared
from .. import style

class KickAngleComponent(QWidget):
    def __init__(self, pv, component):
        super().__init__()
        self.pv = pv
        self.component = component
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        # Toggle between horizontal and vertical
        "#B44141"
        # self.planeRow = QWidget()
        # self.planeRow.setLayout(QHBoxLayout())
        # self.planeRow.layout().setContentsMargins(0, 0, 0, 0)
        # if self.pv.settings['alignment'] == 'Horizontal':
        #     text = 'Aligned to <span style = "color: #bc4444">Horizontal</span> plane.'
        # else:
        #     text = 'Aligned to <span style = "color: #399a26">Vertical</span> plane.'
        # self.state = QLabel(text)
        # self.state.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # self.planeRow.layout().addWidget(self.state)
        # self.toggle = QPushButton('Swap Plane')
        # self.toggle.setFixedSize(100, 35)
        # self.toggle.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#1e1e1e', fontColor = '#c4c4c4'))
        # self.toggle.clicked.connect(self.SwapPlane)
        # self.planeRow.layout().addWidget(self.toggle)
        # self.layout().addWidget(self.planeRow)
        self.slider = slider.SliderComponent(pv, component)
        self.layout().addWidget(self.slider)
        self.UpdateColors()

    # def SwapPlane(self):
    #     if self.pv.settings['alignment'] == 'Horizontal':
    #         self.pv.settings['alignment'] = 'Vertical'
    #         self.state.setText('Aligned to <span style = "color: #399a26">Vertical</span> plane.')
    #     else:
    #         self.pv.settings['alignment'] = 'Horizontal'
    #         self.state.setText('Aligned to <span style = "color: #bc4444">Horizontal</span> plane.')
    #     self.UpdateColors()

    def UpdateColors(self):
        pass
        # if self.pv.settings['alignment'] == 'Vertical':
        #     self.slider.UpdateColors(fillColorDark = "#338522", fillColorLight = "#318720")
        # else:
        #     self.slider.UpdateColors()