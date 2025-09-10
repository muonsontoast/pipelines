from PySide6.QtWidgets import QGraphicsProxyWidget, QGraphicsItemGroup, QWidget
from .. import style

class BoxSelect(QGraphicsProxyWidget):
    def __init__(self, color = "#242424"):
        super().__init__()
        self.color = color
        self.selectedItems:list[QGraphicsProxyWidget] = []
        box = QWidget()
        box.setStyleSheet(style.WidgetStyle(color = self.color, borderRadius = 12))
        self.setZValue(-200)
        self.setWidget(box)