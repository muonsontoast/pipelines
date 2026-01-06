from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget, QSpacerItem
from PySide6.QtCore import Qt
import numpy as np
from ..draggable import Draggable
from ...indicator import Indicator
from ...clickablewidget import ClickableWidget
from ... import shared
from ..socket import Socket
from ... import style

class LinearKernel(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        super().__init__(
            proxy,
            name = kwargs.pop('name', 'Linear Kernel'),
            type = kwargs.pop('type', 'Linear Kernel'),
            size = kwargs.pop('size', [285, 250]),
            # components = {
            #     'value': dict(name = 'Value', value = 0, min = 0, max = 100, default = 0, units = '', type = slider.SliderComponent),
            # },
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

    def Push(self):
        self.clickable = ClickableWidget(self)
        self.clickable.setLayout(QVBoxLayout())
        self.clickable.layout().setContentsMargins(0, 0, 0, 0)
        self.clickable.setObjectName('LinearKernel')
        self.widget = QWidget()
        self.widget.setObjectName('linearKernelHousing')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QGridLayout())
        self.widget.layout().setContentsMargins(15, 5, 15, 10)
        self.widget.layout().setSpacing(10)
        self.header = QWidget()
        self.header.setLayout(QHBoxLayout())
        self.header.layout().setContentsMargins(5, 5, 0, 0)
        self.header.layout().setSpacing(20)
        self.indicator = Indicator(self, 8)
        self.header.layout().addWidget(self.indicator, alignment = Qt.AlignLeft)
        self.title = QLabel(self.name, alignment = Qt.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setObjectName('title')
        self.header.layout().addWidget(self.title)
        self.header.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.widget.layout().addWidget(self.header, 0, 0, 1, 3)
        # graphical display
        self.display = QWidget()
        self.display.setLayout(QVBoxLayout())
        self.display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.display.layout().setContentsMargins(5, 15, 5, 15)
        self.widget.layout().addWidget(self.display, 1, 0, 1, 3)
        # self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.clickable.layout().addWidget(self.widget)
        self.outSocket = Socket(self, 'M', 50, 25, 'right', 'out')
        self.outSocket.setFixedHeight(65)
        self.layout().addWidget(self.clickable)
        self.layout().addWidget(self.outSocket, alignment = Qt.AlignVCenter)
        self.ToggleStyling(active = False)

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
            self.display.setStyleSheet(style.WidgetStyle(color = '#686868'))

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