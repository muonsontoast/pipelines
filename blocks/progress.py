from PySide6.QtWidgets import QWidget, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
import numpy as np
from .. import style

class Progress(QWidget):
    '''A progress bar for actionable blocks to be added to .widget on the entity.'''
    def __init__(self, parent: QWidget, **kwargs):
        super().__init__(parent)
        self.progress = 0
        self.setFixedHeight(30)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(1, 1, 1, 1)
        self.layout().setSpacing(2)
        self.widget = QWidget()
        self.widget.setLayout(QHBoxLayout())
        self.widget.layout().setContentsMargins(2, 2, 2, 2)
        self.layout().addWidget(self.widget)
        self.innerWidget = QWidget()
        self.innerWidget.setLayout(QHBoxLayout())
        self.innerWidget.layout().setContentsMargins(2, 2, 2, 2)
        self.widget.layout().addWidget(self.innerWidget)
        self.bar = QWidget()
        self.innerWidget.layout().addWidget(self.bar, alignment = Qt.AlignLeft)
        self.Reset()
    
    def Reset(self):
        self.progress = 0
        self.bar.setFixedWidth(0)
        self.setStyleSheet(style.WidgetStyle(color = "#3e3e3e", borderRadius = 6))

    def CheckProgress(self, amount):
        '''Takes a decimal in from 0 to 1'''
        self.progress = amount
        if amount == 1:
            self.setStyleSheet(style.WidgetStyle(color = "#2cb158", borderRadius = 6))
        self.bar.setFixedWidth(np.maximum(np.minimum(amount, .97), .04) * self.width())

    def TogglePause(self, isPaused):
        if isPaused:
            self.setStyleSheet(style.WidgetStyle(color = '#FF8811', borderRadius = 6))
        else:
            self.setStyleSheet(style.WidgetStyle(color = '#3e3e3e', borderRadius = 6))