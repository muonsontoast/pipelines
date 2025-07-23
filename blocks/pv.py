from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QHBoxLayout, QSizePolicy, QGraphicsLineItem, QGraphicsProxyWidget
from PySide6.QtCore import Qt, QLineF, QTimer
from PySide6.QtGui import QPen, QColor
from .. import style
from ..draggable import Draggable
from ..indicator import Indicator
from ..clickablewidget import ClickableWidget
from .. import shared
from .. import entity
from ..components import slider
from ..components import link
from ..components import kickangle
from ..components import errors
from .socket import Socket

class PV(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, name, size = (200, 50)):
        super().__init__()
        self.parent = parent
        self.proxy = proxy
        self.hoveringSocket = False
        self.setMouseTracking(True)
        shared.PVs.append(self)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.settings = dict()
        self.settings['name'] = name
        self.settings['size'] = size
        self.active = False
        self.cursorMoved = False
        self.hovering = False
        self.startPos = None
        self.linkTarget = None
        self.links = dict() # link line segments
        self.settings['components'] = {
            'value': dict(name = 'Slider', value = 0, min = 0, max = 100, default = 0, units = 'mrad', type = kickangle.KickAngleComponent),
            'linkedLatticeElement': dict(name = 'Linked Lattice Element', type = link.LinkComponent),
        }
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
        self.clickable.layout().setContentsMargins(0, 0, 0, 0)
        self.clickable.setObjectName('PV')
        self.widget = QWidget()
        self.widget.setObjectName('pvHousing')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QGridLayout())
        self.widget.layout().setContentsMargins(10, 5, 5, 5)
        # Set the size
        size = self.settings.get('size', (300, 100))
        print(f'size of {self.settings['name']} is {size}')
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
        self.links['free'] = QGraphicsLineItem()
        sockets = QWidget()
        sockets.setLayout(QHBoxLayout())
        sockets.layout().setContentsMargins(0, 0, 0, 0)
        self.socket = Socket(self, 'M', size[1], size[1] / 2, 'right')
        sockets.layout().addWidget(self.socket)
        self.layout().addWidget(self.clickable)
        self.layout().addWidget(self.socket)
        self.UpdateColors()

    def UpdateSocketPos(self):
        localPos = self.socket.mapTo(self.proxy.widget(), self.socket.rect().center())
        self.socketPos = self.proxy.scenePos() + localPos

    def mousePressEvent(self, event):
        if self.canDrag:
            super().mousePressEvent(event)
            return
        self.links['free'] = QGraphicsLineItem()
        self.links['free'].setZValue(-20)
        self.links['free'].setPen(QPen(QColor('#c4c4c4'), 8))
        shared.editors[0].scene.addItem(self.links['free'])
        self.dragging = True
        shared.PVLinkSource = self
        shared.activeSocket = self.socket
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.UpdateSocketPos()
        for k, v in self.links.items():
            line = v.line()
            line.setP1(self.socketPos)
            self.links[k].setLine(line)
        if self.dragging:
            self.links['free'].setLine(QLineF(self.socketPos, self.proxy.mapToScene(event.pos())))

    def mouseReleaseEvent(self, event):
        if not self.canDrag:
            self.canDrag = True
            self.dragging = False
            # Hide the link by default
            shared.editors[0].scene.removeItem(self.links['free'])
            super().mouseReleaseEvent(event)
            return
        if not self.cursorMoved:
            if not self.active:
                if shared.selectedPV is not None:
                    if shared.selectedPV != self:
                        shared.selectedPV.startPos = None
                        shared.selectedPV.cursorMoved = False
                        shared.selectedPV.ToggleStyling()
                entity.mainWindow.inspector.Push(self)
                shared.selectedPV = self
                # shared.editorPopup.Push(self.settings)
            else:
                shared.inspector.mainWindowTitle.setText('')
                entity.mainWindow.inspector.Push()
            self.ToggleStyling()
        self.cursorMoved = False
        self.startPos = None
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        if self.canDrag:
            self.hovering = True
            super().enterEvent(event)
        else:
            event.accept()

    def leaveEvent(self, event):
        def logic():
            self.hovering = False
        QTimer.singleShot(0, logic)
        super().leaveEvent(event)
        event.accept()

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
            background-color: #363636;
            border: 2px solid #3d3d3d;
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
            background-color: #565656;
            border: 2px solid #3d3d3d;
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