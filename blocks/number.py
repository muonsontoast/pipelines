from PySide6.QtWidgets import QWidget, QGraphicsProxyWidget, QLineEdit, QSizePolicy, QVBoxLayout
from PySide6.QtCore import Qt
import numpy as np
from .draggable import Draggable
from ..utils.entity import Entity
from .. import shared
from .. import style

class Number(Draggable):
    def __init__(self, parent: Entity, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            proxy, name = kwargs.pop('name', 'Number'), type = 'Number', 
            size = kwargs.pop('size', [200, 100]), headerColor = '#6279B8',
            numberValue = kwargs.pop('numberValue', 1), **kwargs
        )
        self.parent = parent
        self.hasBeenPushed = False
        self.CreateEmptySharedData(np.empty(1))
        self.data[0] = self.settings['numberValue']
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(5, 5, 5, 5)
        self.widget.layout().setSpacing(5)
        self.Push()
    
    def Push(self):
        super().Push()
        self.AddSocket('out', 'M')
        self.main.layout().addWidget(self.widget)
        # add a line edit element
        self.edit = QLineEdit(f'{self.data[0]:.3f}')
        self.edit.setFixedSize(100, 40)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 14))
        self.edit.returnPressed.connect(self.ChangeEdit)
        self.widget.layout().addWidget(self.edit, alignment = Qt.AlignCenter)
        self.ToggleStyling(active = False)

    def Start(self):
        return self.data[0]
    
    def ChangeEdit(self):
        try:
            value = float(self.edit.text())
        except:
            return
        editIdx = self.main.layout().indexOf(self.edit)
        self.main.layout().removeWidget(self.edit)
        self.edit.deleteLater()
        self.data[0] = value
        self.settings['numberValue'] = value
        newEdit = QLineEdit(f'{value:.3f}')
        newEdit.setFixedSize(100, 40)
        newEdit.setAlignment(Qt.AlignCenter)
        newEdit.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 14))
        newEdit.returnPressed.connect(self.ChangeEdit)
        self.edit = newEdit
        self.widget.layout().insertWidget(editIdx, newEdit, alignment = Qt.AlignCenter)

    def BaseStyling(self):
        super().BaseStyling()
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadiusBottomLeft = 8, borderRadiusBottomRight = 8))