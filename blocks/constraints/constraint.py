from PySide6.QtWidgets import QGraphicsProxyWidget, QWidget, QVBoxLayout, QSizePolicy
import numpy as np
from ..draggable import Draggable
from ... import shared
from ... import style

class Constraint(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            proxy,
            name = kwargs.pop('name', 'Constraint'),
            type = kwargs.pop('type', 'Constraint'),
            size = kwargs.pop('size', [300, 150]),
            threshold = kwargs.pop('threshold', 0),
            fontsize = kwargs.pop('fontsize', 12),
            headerColor = "#793E88",
            **kwargs,
        )
        self.parent = parent
        self.fundamental = False
        self.CreateEmptySharedData(np.zeros(2)) # a SET value and a READ value
        self.data[:] = np.inf
        # store the shared memory name and attrs which get copied across instances
        self.dataSharedMemoryName = self.dataSharedMemory.name
        self.dataSharedMemoryShape = self.data.shape
        self.dataSharedMemoryDType = self.data.dtype
        self.widgetStyle = style.WidgetStyle(color = '#2e2e2e', borderRadius = 12, marginRight = 0, fontSize = 14)
        self.widgetSelectedStyle = style.WidgetStyle(color = "#484848", borderRadius = 12, marginRight = 0, fontSize = 14)
        self.Push()
    
    def Push(self):
        super().Push()
        self.AddSocket('in', 'F', acceptableTypes = [Draggable])
        self.AddSocket('out', 'M')
        self.widget = QWidget()
        self.widget.setLayout(QVBoxLayout())
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.layout().setContentsMargins(10, 10, 10, 20)
        self.widget.layout().setSpacing(2)
        self.BaseStyling()

    def CheckState(self):
        pass

    def BaseStyling(self):
        super().BaseStyling()
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontColor = '#c4c4c4', borderRadiusBottomLeft = 8, borderRadiusBottomRight = 8))