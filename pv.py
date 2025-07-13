from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QSizePolicy
from PySide6.QtCore import Qt
from . import style
from .draggable import Draggable
from .indicator import Indicator
from .clickablewidget import ClickableWidget
from . import shared
from . import entity

class PV(Draggable):
    def __init__(self, window, name):
        super().__init__()
        self.setMouseTracking(True)
        shared.PVs.append(self)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.parent = window
        self.setLayout(QGridLayout())
        self.setContentsMargins(1, 1, 1, 1)
        self.settings = dict()
        self.settings['name'] = name
        self.active = False
        self.cursorMoved = False
        self.hovering = False
        self.startPos = None
        # Each component correpsonds to a dropdown in the inspector.
        self.settings['components'] = [
            dict(name = 'Value', value = 0, min = 0, max = 100, units = ''),
            dict(name = 'Linked Lattice Element', value = 0, min = 0, max = 100, units = ''),
        ]
        self.settings['type'] = 'PV'
        self.indicator = None
        self.Push()
    
    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings

    def Push(self):
        self.ClearLayout()
        self.clickable = ClickableWidget(self)
        self.clickable.setLayout(QGridLayout())
        self.clickable.setObjectName('PV')
        self.widget = QWidget()
        self.widget.setObjectName('pvHousing')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QGridLayout())
        self.widget.setContentsMargins(0, 0, 0, 0)
        # Set the size
        size = self.settings.get('size', (250, 80))
        self.setFixedSize(*size)
        self.indicator = Indicator(self, 4)
        self.widget.layout().addWidget(self.indicator, 0, 0, alignment = Qt.AlignLeft)
        name = f'Control PV {self.settings['name'][9:]}' if self.settings['name'][:9] == 'controlPV' else self.settings['name']
        self.title = QLabel(name)
        self.title.setObjectName('title')
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.widget.layout().addWidget(self.title, 0, 1)
        self.widget.layout().addWidget(QWidget(), 1, 1)
        self.clickable.layout().addWidget(self.widget)
        self.layout().addWidget(self.clickable)

        self.UpdateColors()

    def mousePressEvent(self, event):
        self.startPos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.startPos is not None:
            delta = event.pos() - self.startPos
            if (delta.x() ** 2 + delta.y() ** 2) ** .5 > shared.cursorTolerance:
                self.cursorMoved = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.cursorMoved:
            if not self.active:
                if shared.selectedPV is not None:
                    if shared.selectedPV != self:
                        shared.selectedPV.startPos = None
                        shared.selectedPV.cursorMoved = False
                        shared.selectedPV.ToggleStyling()
                entity.mainWindow.inspector.Push(self)
                shared.selectedPV = self
                shared.editorPopup.Push(self.settings)
            else:
                entity.mainWindow.inspector.Push()
            self.ToggleStyling()
        self.cursorMoved = False
        self.startPos = None
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self.hovering = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovering = False
        super().leaveEvent(event)

    def UpdateColors(self):
        if not self.active:
            self.BaseStyling()
            return
        self.SelectedStyling()

    def ToggleStyling(self):
        if self.active:
            self.BaseStyling()
        else:
            self.SelectedStyling()
        self.active = not self.active

    def BaseStyling(self):
        if shared.lightModeOn:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #D2C5A0;
            border: 2px solid #B5AB8D;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            QWidget#title {{
            color: #1e1e1e;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')
        else:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #363636;
            border: 2px solid #1e1e1e;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            QWidget#title {{
            color: #c4c4c4;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')

    def SelectedStyling(self):
        if shared.lightModeOn:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #ECDAAB;
            border: 4px solid #DCC891;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            QWidget#title {{
            color: #1e1e1e;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')
        else:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #5C5C5C;
            border: 4px solid #424242;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            QWidget#title {{
            color: #c4c4c4;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')

    def ClearLayout(self):
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()