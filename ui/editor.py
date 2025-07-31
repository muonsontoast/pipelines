from PySide6.QtWidgets import QFrame, QLabel, QGraphicsScene, QGraphicsView
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter
from .editormenu import EditorMenu
from ..utils.entity import Entity
from .. import shared

class Editor(Entity, QGraphicsView):
    def __init__(self, window, minScale = 3, maxScale = .2):
        '''Scale gets larger the more you zoom in, so `minScale` is max zoom in (> 1) and `maxScale` is max zoom out (< 1)'''
        super().__init__(name = 'Editor', type = Editor)
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
        self.menu = EditorMenu(self)
        self.centerOn(1400, 1400)

        self.startPos = None
        self.currentPos = None
        self.globalStartPos = None
        self.mouseButtonPressed = None

        self.coordsTitle = QLabel()
        self.zoomTitle = QLabel()

        editorPos = self.mapToScene(self.viewport().rect().center())
        self.coordsTitle.setText(f'Editor center: ({editorPos.x():.0f}, {editorPos.y():.0f})')
        self.zoomTitle.setText(f'Zoom: {self.transform().m11() * 100:.0f}%')

    def mousePressEvent(self, event):
        '''Another PV may already be selected so handle this here.'''
        if event is None:
            self.startPos = QPoint(0, 0)
        else:
            self.startPos = self.mapToScene(event.position().toPoint())
        self.globalStartPos = event.position()
        if not self.menu.hidden and shared.PVs[self.menu.ID]['rect'].contains(self.startPos):
            super().mousePressEvent(event)
            return
        for ID, p in shared.PVs.items():
            if p['rect'].contains(self.startPos):
                if ID != self.menu.ID:
                    self.menu.Hide()
                self.canDrag = False
                super().mousePressEvent(event)
                return
        self.menu.Hide()
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.canDrag = True
        self.mouseButtonPressed = event.button()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.currentPos = self.mapToScene(event.position().toPoint())
        if self.mouseButtonPressed == Qt.LeftButton:
            editorPos = self.mapToScene(self.viewport().rect().center())
            self.coordsTitle.setText(f'Editor centre: ({editorPos.x():.0f}, {editorPos.y():.0f})')
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        mousePos = self.mapToScene(event.position().toPoint())
        if self.mouseButtonPressed == Qt.RightButton:
            if not self.menu.ID in shared.PVs.keys() or not shared.PVs[self.menu.ID]['rect'].contains(mousePos):
                self.menu.Show(mousePos - shared.editorMenuOffset)
            event.accept()
            return
        elif not self.canDrag:
            self.setDragMode(QGraphicsView.NoDrag)
            if not self.menu.hidden and shared.PVs[self.menu.ID]['rect'].contains(mousePos):
                super().mouseReleaseEvent(event)
                return
            if self.mouseButtonPressed == Qt.LeftButton:
                for pv in shared.PVs.values():
                    if pv['rect'].contains(mousePos):
                        if pv['pv'] != self.menu:
                            self.menu.Hide()
                        for p in shared.activePVs:
                            if p != pv['pv'] and p.active:
                                p.ToggleStyling(active = False)
        else:
            globalMousePos = event.position()
            delta = globalMousePos - self.globalStartPos
            if delta.x() ** 2 + delta.y() ** 2 < shared.cursorTolerance ** 2: # cursor has been moved.
                for p in shared.activePVs:
                    p.ToggleStyling(active = False)
        super().mouseReleaseEvent(event) # the event needs to propagate beyond the editor to allow drag functionality.
        self.setDragMode(QGraphicsView.NoDrag)

    def wheelEvent(self, event):
        # Check if cursor is over quick menu
        if not self.menu.hidden and shared.PVs[self.menu.ID]['rect'].contains(self.currentPos):
            shared.app.sendEvent(self.menu, event)
            event.accept()
            return
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
        self.zoomTitle.setText(f'Zoom: {self.transform().m11() * 100:.0f}%')
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_Return):
            if not self.menu.hidden:
                shared.app.sendEvent(self.menu, event)
                event.accept()
                return
        super().keyPressEvent(event)

    # This is causing the PV to trigger its redraw twice upon mouse release - look into this to prevent it.
    def DeselectPV(self):
        '''Editor mouseReleaseEvent always triggers, so ignore it if the cursor is inside the PV rect.'''
        shared.selectedPV.cursorMoved = False
        shared.selectedPV.ToggleStyling(active = False)
        shared.selectedPV.startPos = None
        shared.selectedPV = None
        shared.inspector.mainWindowTitle.setText('')
        shared.window.inspector.Push()

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings