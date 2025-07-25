from PySide6.QtWidgets import (
    QFrame, QGraphicsScene, QGraphicsView, QGraphicsProxyWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QCursor
from . import shared
from .blocks import pv
from .blocks import kicker
from .blocks import orbitresponse
from . import entity
from . import editorpopup
from .blocks.socket import Socket
from .blocks.socketinteractable import SocketInteractable

class Editor(QGraphicsView):
    def __init__(self, window):
        super().__init__()
        self.parent = window
        self.settings = dict()
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        # self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setFrameStyle(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setSceneRect(0, 0, 10000, 10000)
        shared.editors.append(self)
        # self.popup = editorpopup.Popup(self, 975, 125, 250, 450)
        # Test widget
        proxy = QGraphicsProxyWidget()
        kickerWidget = kicker.Kicker(self, proxy, 'HSTR5:SETI', size = (215, 50))
        proxy.setWidget(kickerWidget)
        proxy.setPos(1500, 1500)
        self.scene.addItem(proxy)
        shared.proxyPVs[0].append(proxy)
        kickerWidget.UpdateSocketPos()

        proxy = QGraphicsProxyWidget()
        kickerWidget = kicker.Kicker(self, proxy, 'Welp', size = (200, 50))
        proxy.setWidget(kickerWidget)
        proxy.setPos(1500, 1600)
        self.scene.addItem(proxy)
        shared.proxyPVs[0].append(proxy)
        kickerWidget.UpdateSocketPos()

        # Test orbit response
        proxy = QGraphicsProxyWidget()
        orbitResponse = orbitresponse.OrbitResponse(self, proxy, 'Orbit Response l')
        proxy.setWidget(orbitResponse)
        proxy.setPos(1850, 1475)
        self.scene.addItem(proxy)

        proxy = QGraphicsProxyWidget()
        kickerWidget = kicker.Kicker(self, proxy, 'CI:XFER:VSTR:05-01:I', size = (225, 50))
        proxy.setWidget(kickerWidget)
        proxy.setPos(1500, 1700)
        self.scene.addItem(proxy)
        shared.proxyPVs[0].append(proxy)
        kickerWidget.UpdateSocketPos()

        proxy = QGraphicsProxyWidget()
        pvWidget = pv.PV(self, proxy, 'BPM #3', size = (225, 50))
        proxy.setWidget(pvWidget)
        proxy.setPos(1500, 1800)
        self.scene.addItem(proxy)
        shared.proxyPVs[0].append(proxy)
        pvWidget.UpdateSocketPos()
        self.centerOn(1400, 1400)

        self.startPos = None

    def mousePressEvent(self, event):
        self.startPos = event.pos()
        hovering = False
        for p in shared.PVs:
            if p.hovering:
                hovering = True
        if not hovering:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        delta = event.pos() - self.startPos
        hovering = False
        for p in shared.PVs:
            if p.hovering:
                hovering = True
        if not hovering and (delta.x() ** 2 + delta.y() ** 2) ** .5 < shared.cursorTolerance:
            if shared.selectedPV is not None:
                self.DeselectPV()
        super().mouseReleaseEvent(event)

    def DeselectPV(self):
        shared.selectedPV.cursorMoved = False
        shared.selectedPV.ToggleStyling()
        shared.selectedPV.startPos = None
        shared.selectedPV = None
        # shared.editorPopup.objectType.setText('')
        shared.inspector.mainWindowTitle.setText('')
        entity.mainWindow.inspector.Push(deselecting = True)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        zoomFactor = 1 + angle / 1000
        self.scale(zoomFactor, zoomFactor)
        event.accept()

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings