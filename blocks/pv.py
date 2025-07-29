from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QHBoxLayout, QSizePolicy, QGraphicsLineItem, QGraphicsProxyWidget
from PySide6.QtCore import Qt
from .. import style
from .draggable import Draggable
from ..indicator import Indicator
from ..clickablewidget import ClickableWidget
from .. import shared
from ..components import slider
from ..components import link
from ..components import kickangle
from ..components import errors
from .socket import Socket

class PV(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        super().__init__(
            proxy,
            name = kwargs.pop('name', 'PV'),
            type = kwargs.pop('type', PV),
            size = kwargs.pop('size', (200, 50)),
            components = {
                'value': dict(name = 'Slider', value = 0, min = 0, max = 100, default = 0, units = 'mrad', type = slider.SliderComponent),
                'linkedLatticeElement': dict(name = 'Linked Lattice Element', type = link.LinkComponent),
            }
        )
        self.parent = parent
        self.blockType = 'PV'
        self.hoveringSocket = False
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.cursorMoved = False
        self.hovering = False
        self.startPos = None
        self.linkTarget = None
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
        self.clickable.layout().setContentsMargins(0, 0, 0, 0)
        self.clickable.setObjectName('PV')
        self.widget = QWidget()
        self.widget.setObjectName('pvHousing')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QGridLayout())
        self.widget.layout().setContentsMargins(10, 5, 5, 5)
        # Set the size
        size = self.settings.get('size', (200, 50))
        self.setFixedSize(*size)
        self.indicator = Indicator(self, 4)
        self.widget.layout().addWidget(self.indicator, 0, 0, alignment = Qt.AlignLeft)
        name = f'Control PV {self.settings['name'][9:]}' if self.settings['name'][:9] == 'controlPV' else self.settings['name']
        self.title = QLabel(name)
        self.title.setObjectName('title')
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.widget.layout().addWidget(self.title, 0, 1)
        self.widget.layout().addWidget(QWidget(), 1, 1) # padding
        self.clickable.layout().addWidget(self.widget)
        self.linksOut['free'] = QGraphicsLineItem()
        self.outputSocket = Socket(self, 'M', size[1], size[1] / 2, 'right', 'output')
        self.layout().addWidget(self.clickable)
        self.layout().addWidget(self.outputSocket)
        self.UpdateColors()

    def mouseReleaseEvent(self, event):
        # Store temporary values since Draggable overwrites them in its mouseReleaseEvent override.
        isActive = self.active
        hasCursorMoved = self.cursorMoved
        canDrag = self.canDrag
        super().mouseReleaseEvent(event)
        if not canDrag:
            return
        if not hasCursorMoved:
            if not isActive:
                # entity.mainWindow.inspector.Push(self)
                shared.window.inspector.Push(self)
                shared.selectedPV = self
                # shared.editorPopup.Push(self.settings)
            else:
                shared.inspector.mainWindowTitle.setText('')
                shared.window.inspector.Push()
                # entity.mainWindow.inspector.Push()

    def UpdateColors(self):
        if not self.active:
            self.BaseStyling()
            return
        self.SelectedStyling()

    def BaseStyling(self):
        if shared.lightModeOn:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #D2C5A0;
            border: 2px solid #B5AB8D;
            border-top-left-radius: 6px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 0px;
            border-bottom-left-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            QLabel {{
            color: #1e1e1e;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')
        else:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #2e2e2e;
            border: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 0px;
            border-bottom-left-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            QLabel {{
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
            QLabel {{
            color: #c4c4c4;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')
        else:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #3e3e3e;
            border-top-left-radius: 6px;
            border-top-right-radius: 0px;
            border-bottom-right-radius: 0px;
            border-bottom-left-radius: 6px;
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