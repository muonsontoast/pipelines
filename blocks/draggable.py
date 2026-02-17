from PySide6.QtWidgets import QGraphicsProxyWidget, QComboBox, QListWidget, QListWidgetItem, QWidget, QSpacerItem, QPushButton, QLabel, QGraphicsLineItem, QHBoxLayout, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QPen, QColor
from PySide6.QtCore import Qt, QLineF, QPoint, QPointF
import time
from threading import Lock, Event
# from multiprocessing import Event
from ..components.slider import SliderComponent
from ..utils.entity import Entity
from ..utils.transforms import MapDraggableRectToScene
from .socket import Socket
from ..utils.multiprocessing import TogglePause, StopAction
from .. import style
from .. import shared

class Draggable(Entity, QWidget):
    # action block types - these trigger shared memory creation by downstream blocks when propagating up the heirarchy
    actionBlockTypes = ['Single Task GP', 'ORM', 'SVD']
    pvBlockTypes = ['PV', 'Corrector', 'BPM', 'BCM']

    def __init__(self, proxy, **kwargs):
        self.headerColor = kwargs.pop('headerColor', '#2e2e2e')
        dtypes = kwargs.pop('dtypes', ['CHARGE', 'X', 'Y', 'PX', 'PY', 'SURVIVAL_RATE'])
        dtype = kwargs.pop('dtype', None)
        dtype = dtypes[0] if dtype is None else dtype
        super().__init__(name = kwargs.pop('name', 'Draggable'), type = kwargs.pop('type', 'Draggable'), size = kwargs.pop('size', [500, 440]), dtype = dtype, dtypes = dtypes, **kwargs)
        self.fundamental = True
        self.proxy = proxy
        self.lock = Lock()
        self.valueRequest, self.valueReady = Event(), Event()
        self.checkThread = None # every draggable has an optional check thread responsible for updating its value displayed to the user regularly.
        self.stopCheckThread = Event() # force the check thread to close when exiting and saving.
        self.checkThreadIsClosed = Event()
        self.groupID = None # a reference to a group
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
        self.shouldUpdateValue = True # triggers block recalculation and any relevant upstream heirarchies during a run.
        self.pollActionRate = kwargs.get('pollActionRate', 4) # Hz
        self.timeBetweenPolls = 1 / self.pollActionRate * 1e3 # in ms
        # instructions on how to display different data streams, based on the data held in the block.
        # will be deprecated in a future version -- being replaced with self.settings['dtypes']
        ########
        self.streams = {
            'default': lambda: {'data': self.data},
        }
        #########
        self.streamTypesIn = dict() # dict of ID: stream type for incoming blocks
        self.timer = None # cumulative time since last clock update.
        self.clock = None
        self.offlineAction = None
        self.onlineAction = None
        self.timeout = 1 / shared.UIMoveUpdateRate # seconds between move draws.
        self.hovering = False
        self.startPos = None
        self.linkedElementAttrs = dict() # A dict of functions that retrieve information exposed by the linked underlying PyAT element.
        self.canRun = False # indicates that a block can run an action.
        self.editorWidgetsHaveBeenCached = False # ensures caching only happens once when this block is dragged at the start.
        self.FSocketWidgets = QWidget()
        self.FSocketWidgets.setLayout(QVBoxLayout())
        self.FSocketWidgets.layout().setContentsMargins(0, 0, 0, 0)
        self.MSocketWidgets = QWidget()
        self.MSocketWidgets.setLayout(QVBoxLayout())
        self.MSocketWidgets.layout().setContentsMargins(0, 0, 0, 0)
        self.main = QWidget()
        self.main.setLayout(QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)
        self.main.layout().setSpacing(0)
        self.main.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if kwargs.pop('addToShared', True):
            shared.PVs[self.ID] = dict(pv = self, rect = MapDraggableRectToScene(self))
        if self.type == 'PV':
            shared.PVIDs.extend([self.ID])
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def __setattr__(self, name, value):
        if name == 'name' and hasattr(self, 'ID'):
            shared.workspace.assistant.PushMessage(f'Entity {self.ID} name changed to: {value}')
        super().__setattr__(name, value)

    def Push(self):
        # Add widget sections to the layout.
        self.layout().addWidget(self.FSocketWidgets)
        self.AddHeader(isGroup = self.type == 'Group')
        self.layout().addWidget(self.main)
        self.layout().addWidget(self.MSocketWidgets)
        if any(match in self.type for match in ['GP', 'Orbit Response', 'Group']):
            self.widget = QWidget()
            self.widget.setLayout(QVBoxLayout())
            self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.widget.setContentsMargins(0, 5, 0, 5)
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontColor = '#c4c4c4', borderRadiusBottomLeft = 12, borderRadiusBottomRight = 12))
            self.main.layout().addWidget(self.widget)
            if self.type != 'Group':
                self.AddButtons()

    def GetSocketPos(self, name):
        try: 
            socket = getattr(self, f'{name}Socket')
        except:
            return -1
        anchor = QPointF(30, socket.rect().height() / 2) # add a small horizontal pad for display tidiness
        localPos = socket.mapTo(self.proxy.widget(), anchor)
        return self.proxy.mapToScene(localPos)
    
    def GetType(self, ID):
        '''Drills down into tree to find leaf node type.'''
        if len(shared.entities[ID].linksIn) > 0:
            return self.GetType(next(iter(shared.entities[ID].linksIn)))
        fundamentalType = type(shared.entities[ID])
        return fundamentalType if shared.entities[ID].fundamental else shared.entities[ID].__class__.__base__

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
        if not self.editorWidgetsHaveBeenCached:
            shared.activeEditor.SetCacheMode(widgetToIgnore = self.proxy)
            self.editorWidgetsHaveBeenCached = True
        self.timer = time.time() - self.clock
        # in general, draw less often than the mouseMoveEvent is triggered to improve performance.
        if self.timer > self.timeout:
            self.clock = time.time()
            self.timer = 0
            self.HandleMouseMove(event.position(), event.buttons())
        event.accept()

    def mouseReleaseEvent(self, event):
        if event is None:
            return
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
                if self.active:
                    shared.selected = [self.ID]
                else: shared.selected.pop(shared.selected.index(self.ID))
            else:
                finalPos = self.proxy.pos()
                self.settings['position'] = [finalPos.x(), finalPos.y()]
                shared.activeEditor.SetCacheMode('None')
        self.editorWidgetsHaveBeenCached = False
        self.startDragPos = None
        self.cursorMoved = False
        event.accept()

    def MoveBlock(self, startDragPos, mousePos):
        mousePosInSceneCoords = self.proxy.mapToScene(mousePos)
        startDragPosInSceneCoords = self.proxy.mapToScene(startDragPos)
        newPos = self.proxy.pos() + mousePosInSceneCoords - startDragPosInSceneCoords
        self.proxy.setPos(newPos)
        self.settings['position'] = [newPos.x(), newPos.y()]
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
        shared.activeEditor.scene.update()

    def HandleMouseMove(self, mousePos, buttons):
        mousePosInSceneCoords = self.proxy.mapToScene(mousePos)
        if not self.canDrag:
            # Move the end point of the free link coming out the block.
            if self.dragging:
                outputSocketPos = self.GetSocketPos('output')
                self.linksOut['free']['link'].setLine(QLineF(outputSocketPos, mousePosInSceneCoords))
        elif buttons & Qt.LeftButton and self.startDragPos:
            self.cursorMoved = True
            if self.groupID is not None:
                blocksToMove = shared.entities[self.groupID].groupBlocks
            elif self.type == 'Group':
                blocksToMove = self.groupBlocks
            else:
                blocksToMove = shared.activeEditor.area.selectedBlocks
            if len(blocksToMove) > 1:
                for block in blocksToMove:
                    block.MoveBlock(self.startDragPos, mousePos)
            else:
                self.MoveBlock(self.startDragPos, mousePos)
            shared.activeEditor.scene.blockSignals(False)

    def ToggleStyling(self, **kwargs):
        '''Supply an `active` bool to force the active state.'''
        if shared.editorSelectMode and self.type == 'PV':
            return
        active = kwargs.get('active', None) # this is a target, rather than current state, so opposite logic to self.active
        if active is not None:
            if not active:
                if shared.selectedPV == self:
                    shared.selectedPV = None
                if self in shared.activePVs:
                    shared.activePVs.remove(self)
                self.BaseStyling()
                self.active = False
            else:
                shared.selectedPV = self
                if self not in shared.activePVs:
                    shared.activePVs.append(self)
                self.SelectedStyling()
                self.active = True
            return
        if self.active:
            if shared.selectedPV == self:
                shared.selectedPV = None
            shared.activePVs.remove(self)
            self.BaseStyling()
        else:
            shared.activePVs.append(self)
            self.SelectedStyling()
        self.active = not self.active

    def BaseStyling(self):
        if hasattr(self, 'header'):
            self.header.setStyleSheet(style.WidgetStyle(color = self.headerColor, fontSize = 16, borderRadiusTopLeft = 8, borderRadiusTopRight = 8))

    def SelectedStyling(self):
        pass

    def UpdateColors(self):
        pass

    def SetRect(self):
        shared.PVs[self.ID]['rect'] = MapDraggableRectToScene(self)

    def CheckState(self):
        '''Checks whether the block will run in online or offline (physics engine) mode.'''
        online = True
        for ID in self.linksIn:
            if hasattr(shared.entities[ID], 'PVMatch'):
                if not shared.entities[ID].PVMatch:
                    online = False
            else: online = False
        self.online = online
        for ID in self.linksOut:
            if type(ID) == int:
                shared.entities[ID].CheckState() # propagate the CheckState forwards.

    def CreateSection(self, name, title, sliderSteps, floatdp, disableValue = False):
        housing = QWidget()
        housing.setLayout(QHBoxLayout())
        housing.layout().setContentsMargins(15, 20, 15, 0)
        title = QLabel(title)
        title.setStyleSheet(style.LabelStyle(padding = 0, fontColor = '#c4c4c4'))
        housing.layout().addWidget(title)
        self.widget.layout().addWidget(housing, alignment = Qt.AlignLeft)
        widget = QWidget()
        widget.setFixedHeight(50)
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(15, 10, 15, 0)
        setattr(self, name, QListWidget())
        v = getattr(self, name)
        widget.layout().addWidget(v)
        v.setFocusPolicy(Qt.NoFocus)
        v.setSelectionMode(QListWidget.NoSelection)
        v.setStyleSheet(style.InspectorSectionStyle())
        setattr(self, f'{name}Amount', SliderComponent(self, f'{name}', sliderSteps, floatdp, hideRange = True, paddingBottom = 5, sliderOffset = 0, sliderRowSpacing = 15))
        amount = getattr(self, f'{name}Amount')
        if disableValue:
            amount.value.setEnabled(False)
        amount.setMaximumWidth(320)
        item = QListWidgetItem()
        item.setSizeHint(amount.sizeHint())
        v.addItem(item)
        v.setItemWidget(item, amount)
        self.widget.layout().addWidget(widget)
    
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
            if socketType == 'F':
                socketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            else:
                socketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopRight = 12, borderRadiusBottomRight = 12))
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

    def AddButtons(self, *args):
        '''Specify buttons not to draw by including `<start/pause/reset/clear>` as str args.'''
        # Control buttons
        self.buttons = QWidget()
        buttonsHeight = 35
        self.buttons.setFixedHeight(buttonsHeight)
        self.buttons.setLayout(QHBoxLayout())
        self.buttons.layout().setContentsMargins(15, 2, 15, 10)
        if 'start' not in args:
            self.start = QPushButton('Start')
            self.start.setFixedHeight(buttonsHeight)
            self.start.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#2e2e2e', fontColor = '#c4c4c4'))
            self.start.clicked.connect(lambda: self.Start(changeGlobalToggleState = True))
            self.buttons.layout().addWidget(self.start)
        if 'pause' not in args:
            self.pause = QPushButton('Pause')
            self.pause.setFixedHeight(buttonsHeight)
            self.pause.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#2e2e2e', fontColor = '#c4c4c4'))
            self.pause.clicked.connect(lambda: self.Pause(changeGlobalToggleState = True))
            self.buttons.layout().addWidget(self.pause)
        if 'reset' not in args:
            self.reset = QPushButton('Reset')
            self.reset.setFixedHeight(buttonsHeight)
            self.reset.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#2e2e2e', fontColor = '#c4c4c4'))
            self.reset.clicked.connect(self.Reset)
            self.buttons.layout().addWidget(self.reset)
        if 'clear' not in args:
            self.clear = QPushButton('Clear')
            self.clear.setFixedHeight(buttonsHeight)
            self.clear.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#2e2e2e', fontColor = '#c4c4c4'))
            self.buttons.layout().addWidget(self.clear)
        self.main.layout().addWidget(self.buttons)

    def AddHeader(self, isGroup = False):
        self.header = QWidget()
        self.header.setFixedHeight(40)
        self.header.setLayout(QHBoxLayout())
        self.header.layout().setContentsMargins(15, 0, 5, 0)
        self.title = QLabel(f'{self.settings['name']}', alignment = Qt.AlignCenter)
        self.header.layout().addWidget(self.title, alignment = Qt.AlignLeft)
        if isGroup:
            self.header.setFixedWidth(210)
            self.dropdown = QPushButton('\u25BC')
            self.dropdown.setStyleSheet(style.PushButtonBorderlessStyle(color = 'none', fontColor = '#c4c4c4'))
            self.header.layout().addWidget(self.dropdown, alignment = Qt.AlignRight)
        self.main.layout().addWidget(self.header, alignment = Qt.AlignTop)

    def Start(self, changeGlobalToggleState = True, **kwargs):
        pass

    def Pause(self, changeGlobalToggleState = True):
        if not self.actionFinished.is_set():
            TogglePause(self, changeGlobalToggleState)

    def Reset(self):
        StopAction(self, restart = True)
        shared.workspace.assistant.PushMessage(f'{self.name} has been reset.')

    def AddLinkIn(self, ID:int, socket, streamTypeIn:str = '', updateGroupLinks = True, **kwargs):
        '''`socket` the source is connected to and the `ID` of its parent.\n
        `Z` int for sorting.\n
        `hide` bool for hiding.'''
        self.linksIn[ID] = dict(link = QGraphicsLineItem(), socket = socket)
        self.settings['linksIn'][ID] = socket
        link = self.linksIn[ID]['link'].line()
        link.setP1(shared.entities[ID].GetSocketPos('out'))
        link.setP2(self.GetSocketPos(socket))
        self.linksIn[ID]['link'].setLine(link)
        self.linksIn[ID]['link'].setZValue(kwargs.get('Z', -20))
        self.linksIn[ID]['link'].setPen(QPen(QColor("#323232"), 12))
        if kwargs.pop('hide', False):
            self.linksIn[ID]['link'].hide()
        shared.activeEditor.scene.addItem(self.linksIn[ID]['link'])
        # Add link to this draggable's group if it has one.
        if updateGroupLinks and self.groupID is not None:
            if ID not in shared.entities[self.groupID].settings['IDs']:
                shared.entities[self.groupID].AddLinkIn(ID, 'in', Z = -101, hide = True)
                shared.entities[ID].AddLinkOut(self.groupID, 'in')
        if self.type != 'Group' and shared.entities[ID].groupID is not None and shared.entities[ID].groupID != self.groupID:
            self.AddLinkIn(shared.entities[ID].groupID, socket, Z = -101, hide = True)
            shared.entities[shared.entities[ID].groupID].AddLinkOut(self.ID, socket)
        return True

    # this can be overridden to trigger logic that should run when removing incoming links to a block.
    def RemoveLinkIn(self, ID):
        shared.editors[0].scene.removeItem(self.linksIn[ID]['link'])
        self.linksIn.pop(ID)
        self.settings['linksIn'].pop(ID)
        # Check to see if any group links should be removed.
        if shared.entities[ID].type != 'Group' and shared.entities[ID].groupID is not None:
            shouldRemoveGroupLink = True
            for linkID in self.linksIn:
                if linkID != ID and shared.entities[linkID].groupID == shared.entities[ID].groupID:
                    shouldRemoveGroupLink = False
                    break
            if shouldRemoveGroupLink and self.ID in shared.entities[shared.entities[ID].groupID].linksOut:
                self.RemoveLinkIn(shared.entities[ID].groupID)
                shared.entities[shared.entities[ID].groupID].RemoveLinkOut(self.ID)
            

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