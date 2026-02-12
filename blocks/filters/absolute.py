from PySide6.QtWidgets import QLineEdit, QGraphicsProxyWidget
from PySide6.QtCore import Qt
from .filter import Filter
from ... import shared
from ... import style

class Absolute(Filter):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            parent, 
            proxy,
            name = kwargs.pop('name', 'Absolute'),
            type = kwargs.pop('type', 'Absolute'),
            size = kwargs.pop('size', [265, 100]),
            fontsize = kwargs.pop('fontsize', 12),
            threshold = kwargs.pop('threshold', 0),
            **kwargs,
        )

    def Start(self):
        if len(self.linksIn) > 0:
            ID = next(iter(self.linksIn))
            return abs(shared.entities[ID].Start())
        
    def Push(self):
        super().Push()
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