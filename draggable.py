from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QLineF
from . import shared

class Draggable(QWidget):
    def __init__(self):
        super().__init__()
        self.startDragPosition = None
        self.newPosition = None
        self.cursorMoved = False
        self.canDrag = True
        self.dragging = False
        self.hoveringSocket = None

    def mousePressEvent(self, event):
        if self.canDrag and event.button() == Qt.LeftButton:
            self.cursorMoved = False
            # Calculate offset between click and top-left corner of widget.
            self.startDragPosition = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.startDragPosition:
            self.cursorMoved = True
            self.newPosition = event.globalPosition().toPoint() - self.startDragPosition
            self.move(self.newPosition)
            if self.newPosition is not None and self.startDragPosition is not None:
                dx = self.newPosition.x() - self.startDragPosition.x()
                dy = self.newPosition.y() - self.startDragPosition.y()
                if (dx ** 2 + dy ** 2) ** .5 > shared.cursorTolerance:
                    self.cursorMoved = True
            event.accept()

    def mouseReleaseEvent(self, event):
        self.startDragPosition = None
        event.accept()