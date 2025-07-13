from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, QPoint

class Draggable(QWidget):
    def __init__(self):
        super().__init__()
        self.startDragPosition = None
        self.cursorMoved = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.cursorMoved = False
            # Calculate offset between click and top-left corner of widget.
            self.startDragPosition = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.startDragPosition:
            self.cursorMoved = True
            newPosition = event.globalPosition().toPoint() - self.startDragPosition
            self.move(newPosition)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.startDragPosition = None
        event.accept()