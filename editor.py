from PySide6.QtWidgets import (
    QFrame, QGraphicsScene, QGraphicsView, QGraphicsProxyWidget,
)
from PySide6.QtCore import Qt
from . import shared
from .blocks import pv
from . import entity
from . import editorpopup

class Editor(QGraphicsView):
    def __init__(self, window):
        super().__init__()
        self.parent = window
        self.settings = dict()
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setFrameStyle(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setSceneRect(0, 0, 3000, 3000)
        self.popup = editorpopup.Popup(self, 975, 125, 250, 450)
        # Test widget
        pvWidget = pv.PV(self, 'HSTR5:SETI')
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(pvWidget)
        proxy.setPos(1500, 1500)
        self.scene.addItem(proxy)

        pvWidget = pv.PV(self, 'Welp')
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(pvWidget)
        proxy.setPos(1500, 1650)
        self.scene.addItem(proxy)

        pvWidget = pv.PV(self, 'CI:XFER:VSTR:05-01:I')
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(pvWidget)
        proxy.setPos(1500, 1800)
        self.scene.addItem(proxy)
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
        shared.editorPopup.objectType.setText('')
        shared.inspector.mainWindowTitle.setText('')
        entity.mainWindow.inspector.Push(deselecting = True)

    def wheelEvent(self, event):
        if event.angleDelta().y() != 0:
            return
        super().wheelEvent(event)

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings