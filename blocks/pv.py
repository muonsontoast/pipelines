from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget, QSpacerItem
from PySide6.QtCore import Qt
from multiprocessing.shared_memory import SharedMemory
import numpy as np
import aioca
import asyncio
from qasync import QEventLoop
from .draggable import Draggable
from ..indicator import Indicator
from ..clickablewidget import ClickableWidget
from .. import shared
from ..components import slider
from ..components import link
from ..components import kickangle
from ..components import errors
from .socket import Socket
from .. import style

class PV(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        super().__init__(
            proxy,
            name = kwargs.pop('name', 'PV'),
            type = kwargs.pop('type', 'PV'),
            size = kwargs.pop('size', [325, 115]),
            components = {
                'value': dict(name = 'Value', value = 0, min = 0, max = 100, default = 0, units = '', type = slider.SliderComponent),
                'linkedLatticeElement': dict(name = 'Linked Lattice Element', type = link.LinkComponent),
            },
            **kwargs
        )
        self.parent = parent
        self.indicator = None
        self.widgetStyle = style.WidgetStyle(color = '#2e2e2e', borderRadius = 12, marginRight = 0, fontSize = 16)
        self.widgetSelectedStyle = style.WidgetStyle(color = "#484848", borderRadius = 12, marginRight = 0, fontSize = 16)
        self.indicatorStyle = style.IndicatorStyle(8, color = '#c4c4c4', borderColor = "#b7b7b7")
        self.indicatorSelectedStyle = style.IndicatorStyle(8, color = "#E0A159", borderColor = "#E7902D")
        self.indicatorStyleToUse = self.indicatorStyle
        
        # force a PV's scalar output to be shared at instantiation so modifications are seen by all connected blocks
        self.CreateEmptySharedData(np.zeros(2)) # a SET value and a READ value
        self.data[:] = np.nan
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
        self.Push()

        try:
            asyncio.get_event_loop().create_task(self.FetchReadValue())
        except RuntimeError:
            # loop not installed yet — schedule for next Qt tick
            QTimer.singleShot(0, lambda: asyncio.get_event_loop().create_task(self.FetchReadValue()))

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
        self.title = QLabel(self.name, alignment = Qt.AlignCenter)
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

    async def UpdateInspectorLimits(self, PVName, timeout = 1, makeReadOnly = True):
        '''Attempts to update limits inside the inspector, if they are defined for the PV.'''
        if not makeReadOnly:
            # Make fields editable if there are no strict PV limits.
            if self.active:
                shared.inspector.expandables['value'].widget.minimum.setReadOnly(False)
                shared.inspector.expandables['value'].widget.maximum.setReadOnly(False)
        else:
            try:
                mn = await aioca.caget(PVName + ':IMIN', timeout = timeout)
                mx = await aioca.caget(PVName + ':IMAX', timeout = timeout)
                if mx > mn:
                    if self.active:
                        shared.inspector.expandables['value'].widget.minimum.setText(f'{mn}')
                        shared.inspector.expandables['value'].widget.SetMinimum()
                        shared.inspector.expandables['value'].widget.minimum.setReadOnly(True)
                        shared.inspector.expandables['value'].widget.maximum.setText(f'{mx}')
                        shared.inspector.expandables['value'].widget.SetMaximum()
                        shared.inspector.expandables['value'].widget.maximum.setReadOnly(True)
                        shared.inspector.expandables['value'].widget.Reset()
                    else:
                        self.settings['components']['value']['min'] = mn
                        self.settings['components']['value']['max'] = mx
                        self.settings['components']['value']['default'] = max(min(self.settings['components']['value']['default'], mx), mn)
            except:
                # Make fields editable if there are no strict PV limits.
                if self.active:
                    shared.inspector.expandables['value'].widget.minimum.setReadOnly(False)
                    shared.inspector.expandables['value'].widget.maximum.setReadOnly(False)

    async def Start(self):
        '''Unlike more complex blocks, a PV just returns its current value, indicating the end of a graph.'''
        return self.data[1]

    async def FetchReadValue(self, timeout = 1):
        '''Asynchronously fetch and update current value, without blocking the UI thread.'''
        lastMatch = ''
        while True:
            # check whether the current name is a valid PV.
            PVName = self.name.split(':')[0]
            try: 
                self.data[1] = await aioca.caget(PVName + ':I', timeout = timeout)
                self.settings['components']['value']['default'] = self.data[1]
                self.get.setText(f'{self.data[1]:.3f}')
                if PVName != lastMatch:
                    shared.workspace.assistant.PushMessage(f'{PVName} is a valid PV and is now linked.')
                    # Update units if this is a corrector / steerer.
                    if 'STR' in PVName:
                        self.settings['components']['value']['units'] = 'Amps'
                        shared.inspector.expandables['value'].name = self.settings['components']['value']['name'] + ' (Amps)'
                        shared.inspector.expandables['value'].header.setText(shared.inspector.expandables['value'].header.text.split()[0] + '    (Amps)')
                    await self.UpdateInspectorLimits(PVName)
            except:
                self.data[1] = np.nan
                self.get.setText('N/A')
                self.settings['components']['value']['units'] = ''
                if self.active:
                    shared.inspector.expandables['value'].name = self.settings['components']['value']['name']
                    shared.inspector.expandables['value'].header.setText(shared.inspector.expandables['value'].header.text.split()[0])
                await self.UpdateInspectorLimits(PVName, makeReadOnly = False)
            lastMatch = PVName
            await asyncio.sleep(.2)

    def UpdateLinkedElement(self, slider = None, func = None, event = None, override = None):
        '''`event` should be a mouseReleaseEvent if it needs to be called.'''
        if 'linkedElement' not in self.settings:
            if event:
                return super().mouseReleaseEvent(event)
            return
        linkedType = self.settings['linkedElement'].Type
        if linkedType == 'Corrector':
            idx = 0 if self.settings['alignment'] == 'Horizontal' else 1
            print(f'Trying to set override to {override}')
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
            self.widget.setStyleSheet(self.widgetStyle + self.indicatorStyleToUse)
            self.outSocket.setStyleSheet(style.WidgetStyle(marginLeft = 2))
            self.title.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))
            self.set.setStyleSheet(style.LineEditStyle(color = "#2e2e2e"))
            self.get.setStyleSheet(style.LineEditStyle(color = "#1e1e1e"))

    def SelectedStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(self.widgetSelectedStyle + self.indicatorStyleToUse)
            self.outSocket.setStyleSheet(style.WidgetStyle(marginLeft = 2))
            self.title.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))

    def ClearLayout(self):
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()