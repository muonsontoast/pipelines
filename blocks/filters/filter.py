from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget, QMenu
from PySide6.QtCore import Qt, QPointF
import numpy as np
from ..draggable import Draggable
from ... import shared
from ..socket import Socket
from ... import style

class Filter(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            proxy,
            name = kwargs.pop('name', 'filter'),
            type = kwargs.pop('type', 'Filter'),
            size = kwargs.pop('size', [300, 150]),
            fontsize = kwargs.pop('fontsize', 12),
            headerColor = '#312244',
            **kwargs,
        )
        self.parent = parent
        self.CreateEmptySharedData(np.zeros(2)) # a SET value and a READ value
        self.data[:] = np.nan
        # store the shared memory name and attrs which get copied across instances
        self.dataSharedMemoryName = self.dataSharedMemory.name
        self.dataSharedMemoryShape = self.data.shape
        self.dataSharedMemoryDType = self.data.dtype
        self.widgetStyle = style.WidgetStyle(color = '#2e2e2e', borderRadius = 12, marginRight = 0, fontSize = 14)
        self.widgetSelectedStyle = style.WidgetStyle(color = "#484848", borderRadius = 12, marginRight = 0, fontSize = 14)
        self.Push()
    
    def Push(self):
        super().Push()
        self.AddSocket('in', 'F', acceptableTypes = ['PV', 'Corrector', 'BPM', 'Single Task Gaussian Process', 'Less Than', 'Greater Than', 'Invert', 'Single Control', 'Add', 'Subtract', 'Composition'])
        self.AddSocket('out', 'M')
        self.BaseStyling()

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.main.setStyleSheet(self.widgetStyle)
        super().BaseStyling()