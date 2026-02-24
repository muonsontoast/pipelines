from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget, QSpacerItem
from PySide6.QtCore import Qt, Signal
import numpy as np
import aioca
import asyncio
from threading import Thread
from .draggable import Draggable
from ..indicator import Indicator
from ..clickablewidget import ClickableWidget
from .. import shared
from ..components import slider
from ..components import link
from .socket import Socket
from .. import style

class PV(Draggable):
    setTextSignal = Signal(str)
    getTextSignal = Signal(str)
    minimumTextSignal = Signal(str)
    minimumReadOnlySignal = Signal(bool)
    maximumTextSignal = Signal(str)
    maximumReadOnlySignal = Signal(bool)
    defaultReadOnlySignal = Signal(bool)
    headerTextSignal = Signal(str)

    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        super().__init__(
            proxy,
            name = kwargs.pop('name', 'PV'),
            type = kwargs.pop('type', 'PV'),
            size = kwargs.pop('size', [350, 115]),
            components = {
                'value': dict(name = 'Value', value = 0, min = 0, max = 100, default = 0, units = '', type = slider.SliderComponent),
                'linkedLatticeElement': dict(name = 'Linked Lattice Element', type = link.LinkComponent),
            },
            magnitudeOnly = kwargs.pop('magnitudeOnly', False),
            **kwargs
        )
        self.setTextSignal.connect(self.ChangeSetText)
        self.getTextSignal.connect(self.ChangeGetText)
        self.minimumTextSignal.connect(self.ChangeMinimumText)
        self.minimumReadOnlySignal.connect(self.ChangeMinimumReadOnly)
        self.maximumTextSignal.connect(self.ChangeMaximumText)
        self.maximumReadOnlySignal.connect(self.ChangeMaximumReadOnly)
        self.defaultReadOnlySignal.connect(self.ChangeDefaultReadOnly)
        self.headerTextSignal.connect(self.ChangeHeaderText)
        self.parent = parent
        self.indicator = None
        self.widgetStyle = style.WidgetStyle(color = '#2e2e2e', fontColor = '#c4c4c4', borderRadius = 12, marginRight = 0, fontSize = 16)
        self.widgetSelectedStyle = style.WidgetStyle(color = "#484848", fontColor = '#c4c4c4', borderRadius = 12, marginRight = 0, fontSize = 16)
        self.indicatorStyle = style.IndicatorStyle(8, color = '#c4c4c4', borderColor = "#b7b7b7")
        self.indicatorSelectedStyle = style.IndicatorStyle(8, color = "#E0A159", borderColor = "#E7902D") 
        self.indicatorStyleToUse = self.indicatorStyle
        
        # force a PV's scalar output to be shared at instantiation so modifications are seen by all connected blocks
        self.CreateEmptySharedData(np.zeros(2)) # a SET value and a READ value
        self.data[:] = np.inf
        # store the shared memory name and attrs which get copied across instances
        self.dataSharedMemoryName = self.dataSharedMemory.name
        self.dataSharedMemoryShape = self.data.shape
        self.dataSharedMemoryDType = self.data.dtype

        self.streams['default'] = lambda: {
            'data': self.data,
            'default': self.settings['components']['value']['default'],
            'lims': [self.settings['components']['value']['min'], self.settings['components']['value']['max']],
            'alignments': self.settings['alignment'] if 'alignment' in self.settings else None,
            'linkedIdx': self.settings['linkedElement'].Index if 'linkedElement' in self.settings else None,
        }

        self.PVMatch = False
        self.checkStateOfDownstreamBlocks = False
        self.Push()

        self.checkThread = Thread(target = self.FetchAndReadValue)
        self.checkThread.start()

    def ChangeGetText(self, s):
        self.get.setText(s)

    def ChangeSetText(self, s):
        self.set.setText(s)

    def ChangeMinimumText(self, s):
        shared.inspector.expandables['value'].widget.minimum.setText(s)

    def ChangeMinimumReadOnly(self, state):
        shared.inspector.expandables['value'].widget.minimum.setReadOnly(state)

    def ChangeMaximumText(self, s):
        shared.inspector.expandables['value'].widget.maximum.setText(s)

    def ChangeMaximumReadOnly(self, state):
        shared.inspector.expandables['value'].widget.maximum.setReadOnly(state)

    def ChangeDefaultReadOnly(self, state):
        shared.inspector.expandables['value'].widget.default.setReadOnly(state)

    def ChangeHeaderText(self, s = ''):
        if s != '':
            shared.inspector.expandables['value'].header.setText(s)

    def Push(self):
        self.clickable = ClickableWidget(self)
        self.clickable.setLayout(QVBoxLayout())
        self.clickable.layout().setContentsMargins(0, 0, 0, 0)
        self.clickable.setObjectName('PV')
        self.widget = QWidget()
        self.widget.setObjectName('pvHousing')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QGridLayout())
        self.widget.layout().setContentsMargins(15, 5, 5, 5)
        self.header = QWidget()
        self.header.setLayout(QHBoxLayout())
        self.header.layout().setContentsMargins(0, 0, 0, 0)
        self.header.layout().setSpacing(20)
        self.indicator = Indicator(self, 8)
        self.header.layout().addWidget(self.indicator, alignment = Qt.AlignLeft)
        self.title = QLabel(self.name, alignment = Qt.AlignLeft | Qt.AlignVCenter)
        self.title.setFixedWidth(235)
        self.title.setWordWrap(True)
        self.title.setObjectName('title')
        self.header.layout().addWidget(self.title)
        self.header.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.widget.layout().addWidget(self.header, 0, 0, 1, 3)
        self.clickable.layout().addWidget(self.widget)
        self.setget = QWidget()
        self.setget.setLayout(QHBoxLayout())
        self.setget.layout().setContentsMargins(0, 2, 0, 0)
        self.setget.layout().setSpacing(25)
        self.setget.setFixedSize(165, 45)
        self.setWidget = QWidget()
        self.setWidget.setLayout(QVBoxLayout())
        self.setWidget.layout().setContentsMargins(0, 0, 0, 0)
        self.set = QLineEdit('0.000')
        self.set.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.set.setAlignment(Qt.AlignCenter)
        self.setWidget.layout().addWidget(self.set)
        self.setWidget.layout().addWidget(QLabel('SET', alignment = Qt.AlignCenter))
        self.getWidget = QWidget()
        self.getWidget.setLayout(QVBoxLayout())
        self.getWidget.layout().setContentsMargins(0, 0, 0, 0)
        self.get = QLineEdit('N/A')
        self.get.setReadOnly(True)
        self.get.setFocusPolicy(Qt.NoFocus)
        self.get.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.get.setAlignment(Qt.AlignCenter)
        self.getWidget.layout().addWidget(self.get)
        self.getWidget.layout().addWidget(QLabel('READ', alignment = Qt.AlignCenter))
        self.setget.layout().addWidget(self.setWidget, alignment = Qt.AlignLeft)
        self.setget.layout().addWidget(self.getWidget, alignment = Qt.AlignRight)
        self.clickable.layout().addWidget(self.setget, alignment = Qt.AlignHCenter)
        self.outSocket = Socket(self, 'M', 50, 25, 'right', 'out')
        self.outSocket.setFixedHeight(65)
        self.layout().addWidget(self.clickable)
        self.layout().addWidget(self.outSocket, alignment = Qt.AlignTop)
        self.ToggleStyling(active = False)

    def UpdateInspectorLimits(self, PVName, timeout = 1, makeReadOnly = True):
        '''Attempts to update limits inside the inspector, if they are defined for the PV.'''
        if not makeReadOnly:
            # Make fields editable if there are no strict PV limits.
            if self.active:
                self.minimumReadOnlySignal.emit(False)
                self.maximumReadOnlySignal.emit(False)
                self.defaultReadOnlySignal.emit(False)
        else:
            try:
                mn = asyncio.run(
                    aioca.caget(PVName + ':IMIN')
                )
                mx = asyncio.run(
                    aioca.caget(PVName + ':IMAX')
                )
                if mx > mn:
                    if self.active:
                        self.minimumTextSignal.emit(f'{mn}')
                        shared.inspector.expandables['value'].widget.setMinimumSignal.emit()
                        self.minimumReadOnlySignal.emit(True)
                        self.maximumTextSignal.emit(f'{mn}')
                        shared.inspector.expandables['value'].widget.setMaximumSignal.emit()
                        self.maximumReadOnlySignal.emit(True)
                        shared.inspector.expandables['value'].widget.resetSignal.emit()
                    else:
                        self.settings['components']['value']['min'] = float(mn)
                        self.settings['components']['value']['max'] = float(mx)
                        self.settings['components']['value']['default'] = max(min(self.settings['components']['value']['default'], mx), mn)
            except:
                # Make fields editable if there are no strict PV limits.
                if self.active:
                    self.minimumReadOnlySignal.emit(False)
                    self.maximumReadOnlySignal.emit(False)

    def Start(self):
        '''Unlike more complex blocks, a PV just returns its current value, indicating the end of a graph.'''
        return self.data[1] if not self.settings['magnitudeOnly'] else abs(self.data[1])
    
    def FetchAndReadValue(self, timeout = .5):
        '''Asynchronously fetch and update current value, without blocking the UI thread.'''
        lastMatch = ''
        # create event loop used solely by this thread to await aioca command responses.
        while True:
            if self.stopCheckThread.is_set():
                break
            try:
                PVName = self.name
                print('A')
                try:
                    print('B')
                    asyncio.run(
                        aioca.caget(self.name, timeout = 1)
                    )
                    print('C')
                    if self.stopCheckThread.wait(timeout = .25):
                        break
                    print('D')
                    self.data[1] = asyncio.run(
                        aioca.caget(self.name, timeout = 1)
                    )
                    print('E')
                except:
                    print('F')
                    PVName = self.name.split(':')[0]
                    asyncio.run(
                        aioca.caget(PVName + ':I', timeout = 1)
                    )
                    print('G')
                    if self.stopCheckThread.wait(timeout = .25):
                        break
                    print('G1')
                    # set value
                    self.data[0] = asyncio.run(
                        aioca.caget(PVName + ':SETI', timeout = 1)
                    )
                    print('H')
                    # read value
                    self.data[1] = asyncio.run(
                        aioca.caget(PVName + ':I', timeout = 1)
                    )
                if self.stopCheckThread.is_set():
                    break
                try:
                    self.settings['components']['value']['default'] = self.data[1]
                    if PVName != lastMatch:
                        try:
                            self.PVMatch = True
                            self.settings['components']['value']['units'] = ''
                            shared.workspace.assistant.PushMessage(f'{PVName} is a valid PV and is now linked.') # need to move this to Signal system
                            self.checkStateOfDownstreamBlocks = True
                            self.online = True
                            if self.stopCheckThread.is_set():
                                break
                            s = f'{self.data[1]:.3f}' if not np.isnan(self.data[1]) else 'N/A'
                            self.getTextSignal.emit(s)
                            self.setTextSignal.emit(s)
                            self.UpdateUnits(PVName)
                            try:
                                self.UpdateInspectorLimits(PVName)
                            except: pass
                            lastMatch = PVName
                        except Exception as e:
                            print(e)
                    else:
                        s = f'{self.data[1]:.3f}' if not np.isnan(self.data[1]) else 'N/A'
                        self.getTextSignal.emit(s)
                        self.setTextSignal.emit(s)
                except Exception as e:
                    print(e)
            except:
                self.PVMatch = False
                self.online = False
                if not np.isinf(self.data[1]) and not np.isnan(self.data[1]):
                    try:
                        s = f'{self.data[1]:.3f}'
                        if lastMatch != PVName:
                            if self.online:
                                if self.stopCheckThread.is_set():
                                    break
                                self.getTextSignal.emit(s)
                                self.setTextSignal.emit(s)
                            else:
                                if self.stopCheckThread.is_set():
                                    break
                                self.getTextSignal.emit(s)
                                self.setTextSignal.emit(s)
                        else:
                            if self.stopCheckThread.is_set():
                                break
                            self.getTextSignal.emit(s)
                            self.setTextSignal.emit(s)
                    except: pass
                else:
                    with self.lock:
                        if self.stopCheckThread.is_set():
                            break
                        self.getTextSignal.emit('N/A')

                if self.active:
                    try:
                        if lastMatch != PVName:
                            self.UpdateUnits(PVName)
                            shared.inspector.expandables['value'].updateHeaderTextSignal.emit(self.settings['components']['value']['name'], self.settings['components']['value']['units'])
                            self.UpdateInspectorLimits(PVName, makeReadOnly = False)
                        if self.stopCheckThread.is_set():
                                break
                    except: pass
            lastMatch = PVName
            if self.checkStateOfDownstreamBlocks:
                for ID in self.linksOut:
                    if type(ID) == int:
                        shared.entities[ID].CheckState()
            self.checkStateOfDownstreamBlocks = False
            if self.stopCheckThread.wait(timeout = timeout):
                break
        self.checkThreadIsClosed.set()

    def UpdateUnits(self, name):
        if 'STR' in name:
            self.settings['components']['value']['name'] = 'Kick'
            if self.online:
                self.settings['components']['value']['units'] = 'Amps'
            else:
                self.settings['components']['value']['units'] = 'mrad'
        else:
            self.settings['components']['value']['name'] = 'Value'
            self.settings['components']['value']['units'] = ''

    def UpdateLinkedElement(self, slider = None, func = None, event = None, override = None):
        '''`event` should be a mouseReleaseEvent if it needs to be called.'''
        if 'linkedElement' not in self.settings:
            if event:
                return super().mouseReleaseEvent(event)
            return
        linkedType = self.settings['linkedElement'].Type
        if linkedType == 'Corrector':
            idx = 0 if self.settings['alignment'] == 'Horizontal' else 1
            if override is None:
                shared.lattice[self.settings['linkedElement'].Index].KickAngle[idx] = func(slider.value()) * 1e-3 # mrad -> rad
            else:
                shared.lattice[self.settings['linkedElement'].Index].KickAngle[idx] = override * 1e-3 # mrad -> rad
            self.data[0] = shared.lattice[self.settings['linkedElement'].Index].KickAngle[idx]
        elif linkedType == 'Quadrupole':
            if override is None:
                shared.lattice[self.settings['linkedElement'].Index].K = func(slider.value())
            else:
                shared.lattice[self.settings['linkedElement'].Index].K = override
            self.data[0] = shared.lattice[self.settings['linkedElement'].Index].K

    def mouseReleaseEvent(self, event):
        # Store temporary values since Draggable overwrites them in its mouseReleaseEvent override.
        isActive = self.active
        hasCursorMoved = self.cursorMoved
        canDrag = self.canDrag
        super().mouseReleaseEvent(event)
        if not canDrag:
            return
        if not hasCursorMoved:
            # Draggable mouse release event gets called after this PV mouse release event so the shared.selectedPV has not been set yet.
            if not isActive:
                shared.inspector.Push(self)
            else:
                shared.inspector.Push()

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontColor = '#c4c4c4', borderRadius = 12, marginRight = 0, fontSize = 16) + self.indicatorStyleToUse)
            self.outSocket.setStyleSheet(style.WidgetStyle(marginLeft = 2))
            self.title.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))
            self.setWidget.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))
            self.set.setStyleSheet(style.LineEditStyle(color = '#2e2e2e', fontColor = '#c4c4c4'))
            self.getWidget.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))
            self.get.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4'))

    def SelectedStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 12, marginRight = 0, fontSize = 16) + self.indicatorStyleToUse)
            self.outSocket.setStyleSheet(style.WidgetStyle(marginLeft = 2))
            self.title.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))

    def ClearLayout(self):
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()