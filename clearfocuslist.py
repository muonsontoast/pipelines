from PySide6.QtWidgets import QWidget, QListWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from . import style
from . import shared

class ClearFocusListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.overlayHeight = 40

        # Floating overlay on the QListWidget itself, not the viewport
        self.overlay = QWidget(self)
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.overlay.setStyleSheet('background-color: transparent')
        
        self.overlayLayout = QVBoxLayout(self.overlay)
        self.overlayLayout.setAlignment(Qt.AlignTop | Qt.AlignRight)

        self.overlay.resize(200, self.overlayHeight)
        self.overlay.raise_()  # Ensure it's above the scroll area

    def SetName(self, name):
        nameWidget = QLabel(name)
        nameWidget.setStyleSheet('font-size: 14px; font-style: italic;')
        nameWidget.setWordWrap(True)
        nameWidget.setFixedHeight(30)
        nameWidget.setAlignment(Qt.AlignRight)
        nameWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.overlayLayout.addWidget(nameWidget)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.move(210, 5)  # top-left corner

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        item = self.itemAt(event.pos())
        if item is None:
            self.clearSelection()
            self.clearFocus()