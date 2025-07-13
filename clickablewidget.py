from PySide6.QtWidgets import QFrame
from . import entity
from . import shared

class ClickableWidget(QFrame):
    def __init__(self, parentWidget, ):
        super().__init__()
        self.parentWidget = parentWidget
        # self.active = False

    # def mouseReleaseEvent(self, event):
    #     self.parentWidget.mouseReleaseEvent(event)
    #     if not self.parentWidget.cursorMoved:
    #         if not self.active:
    #             self.active = True
    #             entity.mainWindow.inspector.Push(self.parentWidget)
    #             shared.selectedPV = self.parentWidget
    #         else:
    #             self.active = False
    #             entity.mainWindow.inspector.Push()
    #             shared.selectedPV = None
    #     event.accept()