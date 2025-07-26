from PySide6.QtWidgets import (
    QFrame, QGraphicsScene, QGraphicsView, QGraphicsProxyWidget,
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter
from . import shared
from .blocks import pv
from .blocks import kicker
from .blocks import bpm
from .blocks import orbitresponse
from .blocks import view
from . import entity
from . import editorpopup
from .utils.transforms import MapDraggableRectToScene

class Editor(QGraphicsView):
    def __init__(self, window, minScale = 3, maxScale = .2):
        '''Scale gets larger the more you zoom in, so `minScale` is max zoom in (> 1) and `maxScale` is max zoom out (< 1)'''
        super().__init__()
        self.parent = window
        self.settings = dict()
        self.minScale = minScale
        self.maxScale = maxScale
        self.canDrag = False
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
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
        # kickerWidget.UpdateSocketPos()

        proxy = QGraphicsProxyWidget()
        kickerWidget = kicker.Kicker(self, proxy, 'Welp', size = (200, 50))
        proxy.setWidget(kickerWidget)
        proxy.setPos(1500, 1600)
        self.scene.addItem(proxy)
        shared.proxyPVs[0].append(proxy)
        # kickerWidget.UpdateSocketPos()

        # Test orbit response
        proxy = QGraphicsProxyWidget()
        orbitResponse = orbitresponse.OrbitResponse(self, proxy, 'Orbit Response')
        proxy.setWidget(orbitResponse)
        # v = view.View(self, proxy, 'View')
        # proxy.setWidget(v)
        proxy.setPos(1850, 1475)
        self.scene.addItem(proxy)

        proxy = QGraphicsProxyWidget()
        kickerWidget = kicker.Kicker(self, proxy, 'CI:XFER:VSTR:05-01:I', size = (225, 50))
        proxy.setWidget(kickerWidget)
        proxy.setPos(1500, 1700)
        self.scene.addItem(proxy)
        shared.proxyPVs[0].append(proxy)
        # kickerWidget.UpdateSocketPos()

        proxy = QGraphicsProxyWidget()
        bpmWidget = bpm.BPM(self, proxy, 'BPM #3', size = (225, 50))
        proxy.setWidget(bpmWidget)
        proxy.setPos(1500, 1800)
        self.scene.addItem(proxy)
        shared.proxyPVs[0].append(proxy)
        # bpmWidget.UpdateSocketPos()
        self.centerOn(1400, 1400)

        # startPos tracks cursor position upon press in scene coords.
        self.startPos = None
        # globalStartPos tracks global cursor position in window -- necessary since startPos doesn't change with drag.
        self.globalStartPos = None

    def mousePressEvent(self, event):
        '''Another PV may already be selected so handle this here.'''
        if event is None:
            self.startPos = QPoint(0, 0)
        else:
            self.startPos = self.mapToScene(event.position().toPoint())
        self.globalStartPos = event.position()
        for p in shared.PVs:
            rect = MapDraggableRectToScene(p)
            if rect.contains(self.startPos):
                self.canDrag = False
                super().mousePressEvent(event)
                return
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.canDrag = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.canDrag:
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            mousePos = self.mapToScene(event.position().toPoint())
            globalMousePos = event.position()
            delta = globalMousePos - self.globalStartPos
            hovering = False
            for p in shared.PVs:
                rect = MapDraggableRectToScene(p)
                if rect.contains(self.startPos):
                    hovering = True
                    self.setDragMode(QGraphicsView.NoDrag)
                    break
            # Have we clicked outside of any PVs, considering cursor tolerance?
            if not hovering and delta.x() ** 2 + delta.y() ** 2 > shared.cursorTolerance ** 2:
                super().mouseReleaseEvent(event)
                return
            # Is a PV already selected?
            if shared.selectedPV:
                PVRectInSceneCoords = MapDraggableRectToScene(shared.selectedPV)
                if not PVRectInSceneCoords.contains(mousePos):
                    self.DeselectPV()
        super().mouseReleaseEvent(event) # the event needs to propagate beyond the editor to allow drag functionality.
        if self.canDrag:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.startPos = None

    # This is causing the PV to trigger its redraw twice upon mouse release - look into this to prevent it.
    def DeselectPV(self):
        '''Editor mouseReleaseEvent always triggers, so ignore it if the cursor is inside the PV rect.'''
        shared.selectedPV.cursorMoved = False
        shared.selectedPV.ToggleStyling()
        shared.selectedPV.startPos = None
        shared.selectedPV = None
        # shared.editorPopup.objectType.setText('')
        shared.inspector.mainWindowTitle.setText('')
        entity.mainWindow.inspector.Push(deselecting = True)

    def wheelEvent(self, event):
        if event is None:
            return
        angle = event.angleDelta().y()
        zoomFactor = 1 + angle / 1000
        # get current scale
        currentScale = self.transform().m11()
        if (currentScale * zoomFactor > self.minScale) or (currentScale * zoomFactor < self.maxScale):
            event.accept()
            return
        self.scale(zoomFactor, zoomFactor)
        print('Zoom scale is', self.transform().m11())
        event.accept()

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings