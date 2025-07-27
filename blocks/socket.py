from PySide6.QtWidgets import QFrame, QLabel, QGraphicsLineItem, QHBoxLayout
from PySide6.QtCore import Qt, QSize, QLineF, QRect
from PySide6.QtGui import QPen, QColor
from .socketinteractable import SocketInteractable
from .. import style
from .. import shared

class Socket(QFrame):
    '''Accepts kwargs `borderTopLeftRadius`, `borderTopRightRadius`, `borderBottomRightRadius`, `borderBottomLeftRadius`, `contentOffset`'''
    def __init__(self, parent, socketType, width, radius, alignment = 'left', name = '', acceptableTypes = list(), **kwargs):
        '''`type` should be a string <M/F/MF>\n
        M = extend links\n
        F = receive links\n
        MF = extend and receive links\n
        `acceptableTypes` is a list of valid block types that may connect.'''
        super().__init__()
        self.parent = parent
        self.setFixedSize(width, width)
        self.setLayout(QHBoxLayout())
        contentOffset = kwargs.get('contentOffset', (0, 0, 0, 0))
        self.layout().setContentsMargins(*contentOffset)
        self.alignment = alignment
        self.startPos = None
        self.hoveringSocket = False
        self.setMouseTracking(True) 
        # A dict of links to other blocks
        # self.links = dict()
        self.activeLink = None
        self.position = self.pos()
        self.radius = radius
        self.type = socketType
        self.socket = SocketInteractable(self, radius * 2, socketType, alignment, acceptableTypes = acceptableTypes)
        self.layout().addWidget(self.socket)
        self.width = width
        self.name = name
        self.UpdateColors()

    def mousePressEvent(self, event):
        if self.type == 'F':
            super().mousePressEvent(event)
            return
        print('creating a link')
        self.parent.linksOut['free'] = QGraphicsLineItem()
        self.parent.linksOut['free'].setZValue(-20)
        self.parent.linksOut['free'].setPen(QPen(QColor('#c4c4c4'), 8))
        shared.editors[0].scene.addItem(self.parent.linksOut['free'])
        print('link added to scene')
        self.parent.dragging = True
        self.parent.canDrag = False
        shared.PVLinkSource = self.parent
        shared.activeSocket = self
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        print('moving over', self.name)
        socketPos = self.parent.GetSocketPos(self.name)
        if self.parent.dragging:
            self.parent.linksOut['free'].setLine(QLineF(socketPos, self.parent.proxy.mapToScene(self.mapTo(self.parent, event.position().toPoint()))))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # hide the free link by default.
        shared.editors[0].scene.removeItem(self.parent.linksOut['free'])
        super().mouseReleaseEvent(event)

    def UpdateColors(self):
        if self.alignment == 'right':
            self.setStyleSheet(f'background-color: transparent; margin-left: {0 * self.width}px')
        else:
            self.setStyleSheet(f'background-color: transparent; margin-left: {0 * self.width}px')

    def sizeHint(self):
        return QSize(self.socket.diameter, self.socket.diameter)