from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget, QMenu
from PySide6.QtCore import Qt, QPointF
import numpy as np
from .filter import Filter
from ..draggable import Draggable
from ... import shared
from ..socket import Socket
from ... import style

class GreaterThan(Filter):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            parent, 
            proxy,
            name = kwargs.pop('name', 'Greater Than (Filter)'),
            type = kwargs.pop('type', 'Greater Than'),
            size = kwargs.pop('size', [350, 150]),
            fontsize = kwargs.pop('fontsize', 12),
            threshold = kwargs.pop('threshold', 0),
            **kwargs,
        )

    def Start(self):
        print('Starting!')
        if len(self.linksIn) > 0:
            ID = next(iter(self.linksIn))
            print('My value is', np.maximum(shared.entities[ID].data[1], self.settings['threshold']))
            return np.maximum(shared.entities[ID].data[1], self.settings['threshold'])
        
    def Push(self):
        super().Push()
        # add a label
        self.thresholdLabel = QLabel('Threshold')
        self.thresholdLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 14, padding = 0))
        self.main.layout().addWidget(self.thresholdLabel, alignment = Qt.AlignCenter)
        # add a line edit element
        self.edit = QLineEdit(f'{self.settings['threshold']:.3f}')
        self.edit.setFixedSize(100, 40)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 14))
        self.edit.returnPressed.connect(self.ChangeEdit)
        self.main.layout().addWidget(self.edit, alignment = Qt.AlignCenter)
        # for testing
        btn = QPushButton('START')
        btn.setFixedSize(80, 30)
        self.main.layout().addWidget(btn, alignment = Qt.AlignCenter)
        btn.pressed.connect(self.Start)

    def ChangeEdit(self):
        try:
            value = float(self.edit.text())
        except:
            return
        editIdx = self.main.layout().indexOf(self.edit)
        self.main.layout().removeWidget(self.edit)
        self.edit.deleteLater()
        newEdit = QLineEdit(f'{value:.3f}')
        newEdit.setFixedSize(100, 40)
        newEdit.setAlignment(Qt.AlignCenter)
        newEdit.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 14))
        newEdit.returnPressed.connect(self.ChangeEdit)
        self.edit = newEdit
        self.main.layout().insertWidget(editIdx, newEdit, alignment = Qt.AlignCenter)
        self.settings['threshold'] = value