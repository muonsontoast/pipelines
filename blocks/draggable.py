from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QLineF, QPointF
import time
from ..utils.entity import Entity
from ..utils.transforms import MapDraggableRectToScene
from .. import shared

class Draggable(Entity, QWidget):
    def __init__(self, proxy, **kwargs):
        super().__init__(name = kwargs.pop('name', 'Draggable'), type = kwargs.pop('type', Draggable), **kwargs)
        self.proxy = proxy
        self.blockType = 'Draggable'
        self.active = False
        self.startDragPosition = None
        self.newPosition = None
        self.cursorMoved = False
        self.canDrag = True
        self.dragging = False
        self.hoveringSocket = None
        self.FSocketNames = []
        self.linksIn = dict()
        self.linksOut = dict()
        self.data = None # holds the data which is accessed by downstream blocks.
        self.streams = dict() # instructions on how to display different data streams, based on the data held in the block.
        self.timer = None # cumulative time since last clock update.
        self.clock = None
        self.action = None
        self.timeout = 1 / shared.UIMoveUpdateRate # seconds between move draws.
        self.setFixedSize(*kwargs.get('size', (500, 440)))
        if kwargs.pop('addToShared', True):
            shared.PVs[self.ID] = dict(pv = self, rect = MapDraggableRectToScene(self))

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
            shared.activeEditor.SetCacheMode()
        shared.activeEditor.mouseButtonPressed = event.button()
        event.accept()

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
        else:
            shared.selectedPV = self
            if not self.cursorMoved:
                self.ToggleStyling()
            else:
                shared.activeEditor.SetCacheMode('None')
            
        self.startDragPos = None
        self.cursorMoved = False
        event.accept()

    def HandleMouseMove(self, mousePos, buttons):
        mousePosInSceneCoords = self.proxy.mapToScene(mousePos)
        outputSocketPos = self.GetSocketPos('output')
        if not self.canDrag:
            # Move the end point of the free link coming out the block.
            if self.dragging:
                self.linksOut['free']['link'].setLine(QLineF(outputSocketPos, mousePosInSceneCoords))
        elif buttons & Qt.LeftButton and self.startDragPos:
            delta = mousePosInSceneCoords - self.startDragPos
            if (delta.x() ** 2 + delta.y() ** 2) < shared.cursorTolerance ** 2:
                return
            self.cursorMoved = True
            startDragPosInSceneCoords = self.proxy.mapToScene(self.startDragPos)
            newPos = self.proxy.pos() + mousePosInSceneCoords - startDragPosInSceneCoords
            self.proxy.setPos(newPos)
            self.SetRect()
            shared.activeEditor.scene.blockSignals(True)
            # Batch update all incoming links.
            for name in self.FSocketNames:
                socketPos = self.GetSocketPos(name)
                for v in self.linksIn.values():
                    if v['socket'] == name:
                        line = v['link'].line()
                        line.setP2(socketPos)
                        v['link'].setLine(line)
            # Batch update all outgoing links.
            socketPos = self.GetSocketPos('output')
            for k in self.linksOut.keys():
                line = shared.entities[k].linksIn[self.ID]['link'].line()
                line.setP1(socketPos)
                shared.entities[k].linksIn[self.ID]['link'].setLine(line)
            # Move endpoints of links coming in to the block.
            # for v in self.linksIn.values():
            #     link, socket = v['link'], v['socket']
            #     line = link.line()
            #     line.setP2(self.GetSocketPos(socket))
            #     link.setLine(line)
            # # Move origins of links extending out of the block.
            # for v in self.linksOut.values():
            #     link = v['link']
            #     line = v['link'].line()
            #     line.setP1(outputSocketPos)
            #     link.setLine(line)
            shared.activeEditor.scene.blockSignals(False)

    def ToggleStyling(self, **kwargs):
        '''Supply an `active` bool to force the active state.'''
        active = kwargs.get('active', None) # this is a target, rather than current state, so opposite logic to self.active
        if active is not None:
            if not active:
                if shared.selectedPV == self:
                    shared.selectedPV = None
                if self in shared.activePVs:
                    shared.activePVs.remove(self)
                self.BaseStyling()
                self.active = False
                shared.inspector.mainWindowTitle.setText('')
                shared.inspector.Push()
            else:
                shared.selectedPV = self
                if self not in shared.activePVs:
                    shared.activePVs.append(self)
                self.SelectedStyling()
                self.active = True
            return
        if self.active:
            shared.inspector.mainWindowTitle.setText('')
            shared.inspector.Push()
            if shared.selectedPV == self:
                shared.selectedPV = None
            shared.activePVs.remove(self)
            self.BaseStyling()
        else:
            shared.activePVs.append(self)
            self.SelectedStyling()
        self.active = not self.active

    def BaseStyling(self):
        pass

    def SelectedStyling(self):
        pass

    def UpdateColors(self):
        pass

    def SetRect(self):
        shared.PVs[self.ID]['rect'] = MapDraggableRectToScene(self)

    # this can be overridden to trigger logic that should run when removing incoming links to a block.
    def RemoveLinkIn(self, ID):
        shared.editors[0].scene.removeItem(self.linksIn[ID]['link'])
        self.linksIn.pop(ID)

    # this can be overridden to trigger logic that should run when removing outgoing links from a block.
    def RemoveLinkOut(self, ID):
        self.linksOut.pop(ID)