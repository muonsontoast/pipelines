from PySide6.QtWidgets import QFrame
from . import entity
from . import shared

class ClickableWidget(QFrame):
    def __init__(self, parentWidget, ):
        super().__init__()
        self.parentWidget = parentWidget