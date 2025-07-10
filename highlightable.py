from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCore import Qt

class HighlightableWidget(QFrame):
    '''A widget that changes color when hovered.'''
    def __init__(self, background, selected, hover):
        '''Accepts a `background` and `hover` color (#ABABAB)'''
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(5)
        self.background = background
        self.selected = selected
        self.hover = hover
        self.setStyleSheet(f'background-color: {self.background}')

    def enterEvent(self, event):
        self.setStyleSheet(f'background-color: {self.background}')
        super().enterEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.isSelected = True
            self.setStyleSheet(f'background-color: {self.selected}')
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(f'background-color: {self.background}')
        super().leaveEvent(event)