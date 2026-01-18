from PySide6.QtWidgets import QGraphicsProxyWidget, QWidget, QSizePolicy, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from ..blocks.draggable import Draggable
from .. import style

class GroupMenu(Draggable):
    def __init__(self, parent, **kwargs):
        self.proxy = QGraphicsProxyWidget()
        super().__init__(
            self.proxy,
            name = 'Groups',
            type = 'Group Menu',
            size = [200, 100],
            fontsize = 12,
        )
        self.canDrag = False
        
    def Push(self):
        super().Push()
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(2, 2, 2, 2)
        self.main.layout().addWidget(self.widget)
        self.main.setStyleSheet(style.WidgetStyle(color = 'green'))