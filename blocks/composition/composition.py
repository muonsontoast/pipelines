from PySide6.QtWidgets import QWidget, QLabel, QGraphicsProxyWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem
from PySide6.QtCore import Qt
from ..draggable import Draggable
from ..socket import Socket
from ...ui.runningcircle import RunningCircle
from ... import style
from ... import shared

class Composition(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'Composition'), type = kwargs.pop('type', 'Composition'), size = kwargs.pop('size', [300, 300]), **kwargs)
        self.parent = parent
        self.blockType = 'Add'
        self.runningCircle = RunningCircle()
        self.FSocketWidgets = QWidget()
        self.FSocketWidgets.setFixedSize(50, 50)
        self.FSocketWidgets.setLayout(QVBoxLayout())
        self.FSocketWidgets.layout().setContentsMargins(0, 0, 0, 0)
        self.MSocketWidgets = QWidget()
        self.MSocketWidgets.setFixedSize(50, 50)
        self.MSocketWidgets.setLayout(QVBoxLayout())
        self.MSocketWidgets.layout().setContentsMargins(0, 0, 0, 0)
        self.main = QWidget()
        self.main.setLayout(QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(0, 0, 0, 0)
        self.widget.layout().setSpacing(0)
        self.header = QWidget()
        self.header.setStyleSheet(style.WidgetStyle(color = "#28B55E", borderRadiusTopLeft = 8, borderRadiusTopRight = 8, fontSize = 16, fontColor = '#c4c4c4'))
        self.header.setFixedHeight(40)
        self.header.setLayout(QHBoxLayout())
        self.header.layout().setContentsMargins(15, 0, 5, 0)
        self.title = QLabel(self.settings['name'], alignment = Qt.AlignCenter)
        self.header.layout().addWidget(self.title, alignment = Qt.AlignLeft)
        # Add header to layout
        self.widget.layout().addWidget(self.header)
        # add widget to main
        self.main.layout().addWidget(self.widget)
        # Define sockets.
        self.inSocket = Socket(self, 'F', 50, 25, 'left', 'in', acceptableTypes = ['PV', 'Corrector', 'BPM'])
        self.FSocketWidgets.layout().addWidget(self.inSocket)
        self.FSocketNames.extend(['in'])
        self.outSocket = Socket(self, 'M', 50, 25, 'right', 'out')
        self.MSocketWidgets.layout().addWidget(self.outSocket)
        # Add widget sections to the layout.
        self.layout().addWidget(self.FSocketWidgets)
        self.layout().addWidget(self.main)
        self.layout().addWidget(self.MSocketWidgets)

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.inSocket.setStyleSheet(style.WidgetStyle(marginRight = 2))
            self.outSocket.setStyleSheet(style.WidgetStyle(marginLeft = 2))
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 8))
            self.header.setStyleSheet(style.WidgetStyle(color = "#D42F45", borderRadiusTopLeft = 8, borderRadiusTopRight = 8, fontSize = 16, fontColor = '#c4c4c4'))