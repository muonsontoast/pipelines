from PySide6.QtWidgets import QLabel, QApplication
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtCore import Qt
import sys

class VerticalLabel(QLabel):
    def __init__(self, text = ''):
        super().__init__(text)
        self.setFixedWidth(55)  # Adjust as needed

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.translate(self.width(), 0)
        painter.rotate(90)  # Rotate clockwise 90 degrees
        painter.drawText(0, 0, self.height(), self.width(), Qt.AlignCenter, self.text())