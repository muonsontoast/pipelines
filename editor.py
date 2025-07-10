from PySide6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView, QGraphicsRectItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor
from . import shared

class Editor(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.viewport().setStyleSheet("background: red;")
        self.setFrameStyle(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setSceneRect(0, 0, shared.workspace.width() + 5, shared.workspace.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.scene.sceneRect(), Qt.IgnoreAspectRatio)