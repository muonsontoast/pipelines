from PySide6.QtWidgets import QWidget, QFrame
from .draggable import Draggable
from . import entity
from . import style

class ClickableWidget(QFrame):
    def __init__(self, parentWidget, ):
        super().__init__()
        self.parentWidget = parentWidget
        self.active = False

    def mousePressEvent(self, event):
        self.parentWidget.mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.parentWidget.mouseReleaseEvent(event)
        if not self.parentWidget.cursorMoved:
            if not self.active:
                style.TogglePV(self, 'active')
                self.active = True
                entity.mainWindow.inspector.Push(self.parentWidget)
            else:
                style.TogglePV(self, '')
                self.active = False
                entity.mainWindow.inspector.Push()
        event.accept()