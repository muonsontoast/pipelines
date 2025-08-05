from PySide6.QtWidgets import QWidget, QGraphicsProxyWidget, QSizePolicy, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from .composition import Composition
from ..socket import Socket
from ...utils.entity import Entity
from ... import style
from ... import shared

class Add(Composition):
    '''Add composition block.'''
    def __init__(self, parent: Entity, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(parent, proxy, name = kwargs.pop('name', 'Add'), type = 'Add', size = [250, 100], **kwargs)
        self.Push()

    def Push(self):
        self.ToggleStyling(active = False)

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.main.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 20))
        super().BaseStyling()

    def SelectedStyling(self):
        pass
