from PySide6.QtWidgets import QWidget, QGraphicsProxyWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from ..draggable import Draggable
from ..socket import Socket
from ...ui.runningcircle import RunningCircle
from ... import style
from ... import shared

class Composition(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'Composition'), type = kwargs.pop('type', 'Composition'), size = kwargs.pop('size', [300, 300]))
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