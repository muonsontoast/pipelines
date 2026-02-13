from PySide6.QtWidgets import QLineEdit, QGraphicsProxyWidget
from PySide6.QtCore import Qt
from .filter import Filter
from ... import shared
from ... import style

class GreaterThan(Filter):
    '''Can accept multiple blocks at once, treating each as its own constraint of this type.'''
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            parent, 
            proxy,
            name = kwargs.pop('name', 'Greater Than'),
            type = kwargs.pop('type', 'Greater Than'),
            size = kwargs.pop('size', [265, 100]),
            fontsize = kwargs.pop('fontsize', 12),
            threshold = kwargs.pop('threshold', 0),
            **kwargs,
        )

    def Start(self):
        # if len(self.linksIn) > 0:
        #     ID = next(iter(self.linksIn))
        #     # return np.maximum(shared.entities[ID].data[1], self.settings['threshold'])
        #     return np.maximum(shared.entities[ID].Start(), self.settings['threshold'])
        result = dict()
        for ID in self.linksIn:
            result[ID] = shared.entities[ID].Start()
        return result
        
    def Push(self):
        super().Push()
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