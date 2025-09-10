from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QHBoxLayout, QSizePolicy, QGraphicsLineItem, QGraphicsProxyWidget, QSpacerItem
from PySide6.QtCore import Qt
from multiprocessing.shared_memory import SharedMemory
import numpy as np
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
            size = kwargs.pop('size', [325, 75]),
            components = {
                'value': dict(name = 'Slider', value = 0, min = 0, max = 100, default = 0, units = 'mrad', type = slider.SliderComponent),
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
        self.CreateEmptySharedData(np.zeros(1))
        self.data[:] = np.nan
        # store the shared memory name and attrs which get copied across instances
        self.dataSharedMemoryName = self.dataSharedMemory.name
        self.dataSharedMemoryShape = self.data.shape
        self.dataSharedMemoryDType = self.data.dtype

        # self.streams = {
        #     'default': lambda **kwargs: self.data,
        # }

        self.Push()

    def UpdateValue(self):
        '''This only needs to be called when connected on shift.'''
        pass # perform a caget

    def Push(self):
        self.clickable = ClickableWidget(self)
        self.clickable.setLayout(QGridLayout())
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
        self.outSocket = Socket(self, 'M', 50, 25, 'right', 'out')
        self.layout().addWidget(self.clickable)
        self.layout().addWidget(self.outSocket)
        self.ToggleStyling(active = False)

    def UpdateLinkedElement(self, slider = None, func = None, event = None, override = None):
        '''`event` should be a mouseReleaseEvent if it needs to be called.'''
        if 'linkedElement' not in self.settings:
            if event:
                return super().mouseReleaseEvent(event)
            return
        linkedType = self.settings['linkedElement'].Type
        if linkedType == 'Corrector':
            idx = 0 if self.settings['alignment'] == 'Horizontal' else 1
            if not override:
                shared.lattice[self.settings['linkedElement'].Index].KickAngle[idx] = func(slider.value()) * 1e-3 # mrad -> rad
            else:
                shared.lattice[self.settings['linkedElement'].Index].KickAngle[idx] = override * 1e-3 # mrad -> rad
            self.data[0] = shared.lattice[self.settings['linkedElement'].Index].KickAngle[idx]
        elif linkedType == 'Quadrupole':
            if not override:
                shared.lattice[self.settings['linkedElement'].Index].K = func(slider.value())
            else:
                shared.lattice[self.settings['linkedElement'].Index].K = override
            self.data[0] = shared.lattice[self.settings['linkedElement'].Index].K

        # print(f'{self.name}\'s data has been set to: {self.data}')
        # if not hasattr(self, 'sharedMemory'):
        #     self.sharedMemory = SharedMemory(name = self.dataSharedMemoryName)
        #     self.data = np.ndarray(self.dataSharedMemoryShape, self.dataSharedMemoryDType, buffer = self.sharedMemory.buf)

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