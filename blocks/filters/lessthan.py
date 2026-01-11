from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget
from PySide6.QtCore import Qt
import numpy as np
from .filter import Filter
from ... import shared
from ... import style

class LessThan(Filter):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            parent, 
            proxy,
            name = kwargs.pop('name', 'Less Than (Filter)'),
            type = kwargs.pop('type', 'Less Than'),
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
            return np.minimum(shared.entities[ID].data[1], self.settings['threshold'])
        
    def Push(self):
        super().Push()
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(10, 10, 10, 20)
        # add a label
        self.thresholdLabel = QLabel('Threshold')
        self.thresholdLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 14, padding = 0))
        self.widget.layout().addWidget(self.thresholdLabel, alignment = Qt.AlignCenter)
        # add a line edit element
        self.edit = QLineEdit(f'{self.settings['threshold']:.3f}')
        self.edit.setFixedSize(100, 40)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 14))
        self.edit.returnPressed.connect(self.ChangeEdit)
        self.widget.layout().addWidget(self.edit, alignment = Qt.AlignCenter)
        self.main.layout().addWidget(self.widget)

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
        self.widget.layout().insertWidget(editIdx, newEdit, alignment = Qt.AlignCenter)
        self.settings['threshold'] = value