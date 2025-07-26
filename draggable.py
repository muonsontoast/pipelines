from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QLineF, QPointF
import time
from . import shared

class Draggable(QWidget):
    def __init__(self, proxy, size = (550, 440)):
        super().__init__()
        self.proxy = proxy
        self.active = False
        self.startDragPosition = None
        self.newPosition = None
        self.cursorMoved = False
        self.canDrag = True
        self.dragging = False
        self.hoveringSocket = None
        self.linksIn = dict()
        self.linksOut = dict()
        self.settings = dict()
        self.timer = None # cumulative time since last clock update.
        self.clock = None
        self.timeout = 1 / shared.UIMoveUpdateRate # seconds between move draws.
        self.setFixedSize(*size)
        shared.PVs.append(self)

    def Push(self):
        self.ClearLayout()

    def GetSocketPos(self, name):
        try: 
            socket = getattr(self, f'{name}Socket')
        except:
            return -1
        anchor = QPointF(30, socket.rect().height() / 2) # add a small horizontal pad for display tidiness
        localPos = socket.mapTo(self.proxy.widget(), anchor)
        return self.proxy.scenePos() + localPos

    def ClearLayout(self):
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def mousePressEvent(self, event):
        if self.canDrag and event.button() == Qt.LeftButton:
            self.cursorMoved = False
            self.startDragPos = event.position().toPoint()
            self.clock = time.time()
            self.timer = 0
        event.accept()
        # super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.clock == None:
            return
        self.timer = time.time() - self.clock
        # in general, draw less often than the mouseMoveEvent is triggered to improve performance.
        if self.timer > self.timeout:
            self.clock = time.time()
            self.timer = 0
            self.HandleMouseMove(event.position(), event.buttons())
        event.accept()

    def mouseReleaseEvent(self, event):
        self.clock = None
        self.timer = None
        # Have we drawn a link?
        if not self.canDrag:
            shared.mousePosUponRelease = self.proxy.mapToScene(event.position().toPoint())
            self.dragging = False
            self.canDrag = True
        # Have we only clicked on the PV?
        elif not self.cursorMoved:
            if shared.selectedPV:
                if shared.selectedPV != self:
                    shared.selectedPV.startPos = None
                    shared.selectedPV.cursorMoved = False
                    shared.selectedPV.ToggleStyling()
            if not self.active:
                shared.selectedPV = self
            self.ToggleStyling()
            
        self.startDragPos = None
        self.cursorMoved = False
        super().mouseReleaseEvent(event)

    def HandleMouseMove(self, mousePos, buttons):
        mousePosInSceneCoords = self.proxy.mapToScene(mousePos)
        outputSocketPos = self.GetSocketPos('output')
        if not self.canDrag:
            # Move the end point of the free link coming out the block.
            if self.dragging:
                self.linksOut['free'].setLine(QLineF(outputSocketPos, mousePosInSceneCoords))
        elif buttons & Qt.LeftButton and self.startDragPos:
            delta = mousePosInSceneCoords - self.startDragPos
            if (delta.x() ** 2 + delta.y() ** 2) < shared.cursorTolerance ** 2:
                return
            self.cursorMoved = True
            startDragPosInSceneCoords = self.proxy.mapToScene(self.startDragPos)
            newPos = self.proxy.pos() + mousePosInSceneCoords - startDragPosInSceneCoords
            self.proxy.setPos(newPos)
            # Move endpoints of links coming in to the block.
            for link, socket in self.linksIn.items():
                line = link.line()
                line.setP2(self.GetSocketPos(socket))
                link.setLine(line)
            for k, v in self.linksOut.items():
                line = v.line()
                line.setP1(outputSocketPos)
                self.linksOut[k].setLine(line)

    def ToggleStyling(self):
        if self.active:
            shared.activePVs.append(self)
            self.BaseStyling()
        else:
            shared.activePVs.append(self)
            self.SelectedStyling()
        self.active = not self.active

    def BaseStyling(self):
        pass

    def SelectedStyling(self):
        pass