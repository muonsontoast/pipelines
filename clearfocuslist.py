from PySide6.QtWidgets import QWidget, QListWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from . import style

class ClearFocusListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.overlayHeight = 40

        # Floating overlay on the QListWidget itself, not the viewport
        self.overlay = QWidget(self)
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.overlay.setStyleSheet("background-color: transparent; border-radius: 2px;")
        
        self.overlayLayout = QVBoxLayout(self.overlay)
        self.overlayLayout.setAlignment(Qt.AlignTop | Qt.AlignRight)

        self.overlay.resize(150, self.overlayHeight)
        self.overlay.raise_()  # Ensure it's above the scroll area

    def SetName(self, name):
        nameWidget = QLabel(name)
        nameWidget.setFixedHeight(30)
        nameWidget.setAlignment(Qt.AlignCenter)
        nameWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        style.AdjustLabelColor(nameWidget, style.backgroundColor)
        self.overlayLayout.addWidget(nameWidget)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep the overlay in top-left (or adjust geometry if needed)
        self.overlay.move(250, 5)  # top-left corner

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        item = self.itemAt(event.pos())
        if item is None:
            self.clearSelection()
            self.clearFocus()