from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QSizePolicy
from PySide6.QtCore import Qt
from . import style
from .draggable import Draggable
from .indicator import Indicator
from .clickablewidget import ClickableWidget

class PV(Draggable):
    def __init__(self, window, name):
        super().__init__(window)
        self.parent = window
        self.setLayout(QGridLayout())
        self.setContentsMargins(1, 1, 1, 1)
        self.settings = dict()
        self.settings['name'] = name
        # Each component correpsonds to a dropdown in the inspector.
        self.settings['components'] = [
            dict(name = 'Value', value = 0, min = 0, max = 100, units = ''),
            dict(name = 'Linked Lattice Element', value = 0, min = 0, max = 100, units = ''),
        ]
        self.indicator = None
        self.Push()
    
    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings

    def Push(self):
        # Clear children widgets
        self.ClearLayout()
        self.clickable = ClickableWidget(self)
        self.clickable.setLayout(QGridLayout())
        self.clickable.setObjectName('PV')
        self.clickable.setStyleSheet(style.PVStyle)
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QGridLayout())
        self.widget.setContentsMargins(0, 0, 0, 0)
        # Set the size
        size = self.settings.get('size', (250, 80))
        self.setFixedSize(*size)
        self.indicator = Indicator(self, 4)
        self.widget.layout().addWidget(self.indicator, 0, 0, alignment = Qt.AlignLeft)
        name = f'Control PV {self.settings['name'][9:]}' if self.settings['name'][:9] == 'controlPV' else self.settings['name']
        title = QLabel(name)
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.widget.layout().addWidget(title, 0, 1)
        self.widget.layout().addWidget(QWidget(), 1, 1)
        self.clickable.layout().addWidget(self.widget)
        self.layout().addWidget(self.clickable)

    def ClearLayout(self):
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()