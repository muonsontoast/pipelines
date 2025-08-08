from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QGraphicsLineItem, QHBoxLayout, QVBoxLayout
from PySide6.QtGui import QPen, QColor
from PySide6.QtCore import Qt, QLineF, QPointF
import time
from ..utils.entity import Entity
from ..utils.transforms import MapDraggableRectToScene
from .socket import Socket
from .. import style
from .. import shared

class Draggable(Entity, QWidget):
    def __init__(self, proxy, **kwargs):
        super().__init__(name = kwargs.pop('name', 'Draggable'), type = kwargs.pop('type', 'Draggable'), size = kwargs.pop('size', [500, 440]), **kwargs)
        self.proxy = proxy
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
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
        self.settings['linksIn'] = dict()
        self.settings['linksOut'] = dict()
        self.online = False
        self.streams = dict() # instructions on how to display different data streams, based on the data held in the block.
        self.timer = None # cumulative time since last clock update.
        self.clock = None
        self.offlineAction = None
        self.onlineAction = None
        self.timeout = 1 / shared.UIMoveUpdateRate # seconds between move draws.
        self.hovering = False
        self.startPos = None
        self.linkedElementAttrs = dict() # A dict of functions that retrieve information exposed by the linked underlying PyAT element.
        self.stream = None
        self.canRun = False # indicates that a block can run an action.
        self.FSocketWidgets = QWidget()
        self.FSocketWidgets.setLayout(QVBoxLayout())
        self.FSocketWidgets.layout().setContentsMargins(0, 0, 0, 0)
        self.MSocketWidgets = QWidget()
        self.MSocketWidgets.setLayout(QVBoxLayout())
        self.MSocketWidgets.layout().setContentsMargins(0, 0, 0, 0)
        self.main = QWidget()
        self.main.setLayout(QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(style.WidgetStyle())
        if kwargs.pop('addToShared', True):
            shared.PVs[self.ID] = dict(pv = self, rect = MapDraggableRectToScene(self))
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def Push(self):
        # Add widget sections to the layout.
        self.layout().addWidget(self.FSocketWidgets)
        self.layout().addWidget(self.main)
        self.layout().addWidget(self.MSocketWidgets)

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
        shared.activeEditor.mouseButtonPressed = event.button()
        event.accept()

    def mouseMoveEvent(self, event):
        if self.clock == None:
            return
        shared.activeEditor.SetCacheMode()
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
                finalPos = self.proxy.pos()
                self.settings['position'] = [finalPos.x(), finalPos.y()]
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
            socketPos = self.GetSocketPos('out')
            for k in self.linksOut.keys():
                if k == 'free':
                    continue
                line = shared.entities[k].linksIn[self.ID]['link'].line()
                line.setP1(socketPos)
                shared.entities[k].linksIn[self.ID]['link'].setLine(line)
            self.proxy.update()
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
                # print('Resetting the inspector')
                # shared.inspector.mainWindowTitle.setText('')
                # shared.inspector.Push()
            else:
                shared.selectedPV = self
                if self not in shared.activePVs:
                    shared.activePVs.append(self)
                self.SelectedStyling()
                self.active = True
            return
        if self.active:
            # print(f'{self.name} is already active!')
            # shared.inspector.mainWindowTitle.setText('')
            # shared.inspector.Push()
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
    
    def AddSocket(self, name: str, socketType: str, socketText = '', housingWidth: int = 50, acceptableTypes: list = []) -> Socket:
        '''Leave `housingWidth` as default value for no accompanying socket name.\n
        `socketType` should be <F/M>\n'''
        socketHousing = QWidget()
        socketHousing.setLayout(QHBoxLayout())
        socketHousing.layout().setContentsMargins(0, 0, 0, 0)
        socketHousing.layout().setSpacing(0)
        socketHousing.setFixedSize(housingWidth, 75)
        alignment = 'left' if socketType == 'F' else 'right'
        socket = Socket(self, socketType, 50, 25, alignment, name, acceptableTypes)
        socketHousing.layout().addWidget(socket)
        if socketText != '':
            socketTitle = QLabel(f'{socketText}')
            socketTitle.setObjectName(f'{socketText}SocketTitle')
            socketTitle.setAlignment(Qt.AlignCenter)
            socketHousing.layout().addWidget(socketTitle)
            setattr(self, f'{name}SocketTitle', socketTitle)
        setattr(self, f'{name}SocketHousing', socketHousing)
        setattr(self, f'{name}Socket', socket)
        if alignment == 'left':
            socket.setStyleSheet(style.WidgetStyle(marginRight = 2))
            self.FSocketWidgets.layout().addWidget(getattr(self, f'{name}SocketHousing'), alignment = Qt.AlignRight)
            self.FSocketNames.append(name)
        else:
            socket.setStyleSheet(style.WidgetStyle(marginLeft = 2))
            self.MSocketWidgets.layout().addWidget(getattr(self, f'{name}SocketHousing'), alignment = Qt.AlignLeft)

    def AddButtons(self):
        # Control buttons
        self.buttons = QWidget()
        buttonsHeight = 35
        self.buttons.setFixedHeight(buttonsHeight)
        self.buttons.setLayout(QHBoxLayout())
        self.buttons.layout().setContentsMargins(15, 2, 15, 10)
        self.start = QPushButton('Start')
        self.start.setFixedHeight(buttonsHeight)
        self.start.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#2e2e2e', fontColor = '#c4c4c4'))
        self.start.clicked.connect(self.Start)
        self.pause = QPushButton('Pause')
        self.pause.setFixedHeight(buttonsHeight)
        self.pause.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#2e2e2e', fontColor = '#c4c4c4'))
        self.pause.clicked.connect(self.Pause)
        self.stop = QPushButton('Stop')
        self.stop.setFixedHeight(buttonsHeight)
        self.stop.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#2e2e2e', fontColor = '#c4c4c4'))
        self.stop.clicked.connect(self.Stop)
        self.clear = QPushButton('Clear')
        self.clear.setFixedHeight(buttonsHeight)
        self.clear.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#2e2e2e', fontColor = '#c4c4c4'))
        self.buttons.layout().addWidget(self.start)
        self.buttons.layout().addWidget(self.pause)
        self.buttons.layout().addWidget(self.stop)
        self.buttons.layout().addWidget(self.clear)
        self.main.layout().addWidget(self.buttons)

    def Start(self):
        pass

    def Pause(self):
        pass

    def Stop(self):
        pass

    def AddLinkIn(self, ID, socket):
        '''`socket` the source is connected to and the `ID` of its parent.'''
        self.linksIn[ID] = dict(link = QGraphicsLineItem(), socket = socket)
        self.settings['linksIn'][ID] = socket
        link = self.linksIn[ID]['link'].line()
        link.setP1(shared.entities[ID].GetSocketPos('out'))
        link.setP2(self.GetSocketPos(socket))
        self.linksIn[ID]['link'].setLine(link)
        self.linksIn[ID]['link'].setZValue(-20)
        self.linksIn[ID]['link'].setPen(QPen(QColor("#323232"), 12))
        shared.activeEditor.scene.addItem(self.linksIn[ID]['link'])

    # this can be overridden to trigger logic that should run when removing incoming links to a block.
    def RemoveLinkIn(self, ID):
        shared.editors[0].scene.removeItem(self.linksIn[ID]['link'])
        self.linksIn.pop(ID)
        self.settings['linksIn'].pop(ID)

    def AddLinkOut(self, ID, socket):
        '''`socket` this is linked to and the `ID` of its parent.'''
        self.linksOut[ID] = socket
        self.settings['linksOut'][ID] = socket
        if hasattr(self, 'indicator'):
            self.indicatorStyleToUse = self.indicatorSelectedStyle
            self.ToggleStyling(active = self.active)

    # this can be overridden to trigger logic that should run when removing outgoing links from a block.
    def RemoveLinkOut(self, ID):
        self.linksOut.pop(ID)
        self.settings['linksOut'].pop(ID)
        if hasattr(self, 'indicator'):
            if len(self.linksOut.values()) == 0:
                self.indicatorStyleToUse = self.indicatorStyle
                self.ToggleStyling(active = self.active)
                # self.widget.setStyleSheet(self.widgetStyle + self.indicatorStyleToUse)