from PySide6.QtWidgets import QFrame

class ClickableWidget(QFrame):
    def __init__(self, parentWidget, ):
        super().__init__()
        self.parentWidget = parentWidget