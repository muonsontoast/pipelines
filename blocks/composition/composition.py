from PySide6.QtWidgets import QWidget, QGraphicsProxyWidget, QVBoxLayout, QSizePolicy, QSpacerItem
from ..draggable import Draggable
from ...ui.runningcircle import RunningCircle
from ... import style
from ... import shared

class Composition(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'Composition'), type = kwargs.pop('type', 'Composition'), size = kwargs.pop('size', [300, 300]), headerColor = '#D42F45', **kwargs)
        self.parent = parent
        self.blockType = 'Add'
        self.runningCircle = RunningCircle()
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(5, 5, 5, 5)
        self.widget.layout().setSpacing(5)
        # self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.Push()

    def Push(self):
        super().Push()
        self.main.layout().addWidget(self.widget)
        self.AddSocket('out', 'M')
        self.ToggleStyling(active = False)

    def CheckState(self):
        pass

    def BaseStyling(self):
        super().BaseStyling()
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadiusBottomLeft = 8, borderRadiusBottomRight = 8))