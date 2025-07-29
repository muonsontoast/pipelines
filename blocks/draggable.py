from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QLineF, QPointF, QTimer
import time
from multiprocessing import Process, Queue
from ..utils.entity import Entity
from ..utils.worker import Worker
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
        self.linksIn = dict() # dict of QGraphicsLineItems.
        self.linksOut = dict()
        self.data = None # holds the data which is accessed by downstream blocks.
        self.streams = dict() # instructions on how to display different data streams, based on the data held in the block.
        self.timer = None # cumulative time since last clock update.
        self.clock = None
        self.action = None
        self.timeout = 1 / shared.UIMoveUpdateRate # seconds between move draws.
        self.setFixedSize(*kwargs.get('size', (500, 440)))
        shared.PVs.append(self)

    def Push(self):
        self.ClearLayout()

    # more attention needs to be paid here
    # def PerformAction(self, func, *args):
    #     print('Performing action:', func)
    #     thread = QThread()
    #     worker = Worker(func, *args)
    #     worker.moveToThread(thread)
    #     thread.started.connect(worker.start)
    #     worker.finished.connect(lambda w = worker, t = thread: self.SaveData(w, t))
    #     thread.start()

    # def RunProcess(self, *args):
    #     self.queue.put(self.action.RunOffline(*args))

    # def CheckProcess(self):
    #     if not self.queue.empty():
    #         # kill the process
    #         self.process.terminate()
    #         self.process.join()
    #         self.data = self.queue.get()
    #         if hasattr(self, 'runningCircle'):
    #             self.runningCircle.stop = True

    # def PerformAction(self, *args):
    #     self.queue = Queue()
    #     self.process = Process(target = self.RunProcess, args = (*args,))
    #     self.process.start()
    #     # periodically check if the action has finished ...
    #     self.checkTimer = QTimer()
    #     self.checkTimer.timeout.connect(self.CheckProcess)
    #     self.checkTimer.start(100)

    # def SaveData(self, worker, thread):
    #     print('worker finished and saving data')
    #     self.data = worker.data
    #     worker.deleteLater()
    #     self.CleanUpThread(thread)

    # def CleanUpThread(self, thread):
    #     print('cleaning up thread!')
    #     if hasattr(self, 'runningCircle'):
    #         self.runningCircle.stop = True
    #     if hasattr(self, 'title'):
    #         self.title.setText(self.title.text().split(' (')[0] + ' (Holding Data)')
    #     thread.quit()
    #     thread.deleteLater()

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
            for v in self.linksIn.values():
                link, socket = v['link'], v['socket']
                line = link.line()
                line.setP2(self.GetSocketPos(socket))
                link.setLine(line)
            # Move origins of links extending out of the block.
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