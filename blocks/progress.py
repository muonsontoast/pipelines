from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QSizePolicy, QSpacerItem
from PySide6.QtCore import Qt
import numpy as np
from .. import style

class Progress(QWidget):
    '''A progress bar for actionable blocks to be added to .widget on the entity.'''
    def __init__(self, **kwargs):
        super().__init__()
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
        self.CheckProgress(0)
    
    def Reset(self):
        self.progress = 0
        self.bar.setFixedWidth(0)
        self.bar.setStyleSheet(style.WidgetStyle(color = '#c4c4c4', borderRadius = 4))

    def CheckProgress(self, amount):
        '''Takes a decimal in from 0 to 1'''
        if amount <= self.progress:
            return
        self.progress = amount
        amount = np.maximum(amount, .01)
        if amount > .97:
            if amount > .99:
                self.bar.setStyleSheet(style.WidgetStyle(color = '#FFC100', borderRadius = 4))
            amount = .97
        self.bar.setFixedWidth(amount * self.width())
