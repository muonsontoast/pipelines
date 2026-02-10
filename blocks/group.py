from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget, QSpacerItem
from PySide6.QtCore import Qt, QPoint
from .draggable import Draggable
from .. import shared
from .. import style

class Group(Draggable):
    def __init__(self, parent, proxy:QGraphicsProxyWidget, **kwargs):
        IDs = kwargs.pop('IDs', [])
        if IDs == []:
            self.groupItems = shared.activeEditor.area.selectedItems
            self.groupBlocks = shared.activeEditor.area.selectedBlocks
        else:
            self.groupItems = [shared.entities[ID].proxy for ID in IDs]
            self.groupBlocks = [shared.entities[ID] for ID in IDs]
        numBlocks = kwargs.pop('numBlocks', len(self.groupItems))
        boundingRect = self.groupItems[0].sceneBoundingRect()
        for item in self.groupItems[1:]:
            boundingRect = boundingRect.united(item.sceneBoundingRect())
        super().__init__(
            proxy,
            name = kwargs.pop('name', 'Group'),
            type = kwargs.pop('type', 'Group'),
            size = kwargs.pop('size', [int(boundingRect.width()) + 50, int(boundingRect.height()) + 100]),
            headerColor = "#6A7062",
            numBlocks = numBlocks,
            IDs = IDs,
            **kwargs
        )
        for ID in IDs:
            shared.entities[ID].groupID = self.ID # inform blocks that they belong to this group.
        self.groupBlocks.append(self)
        self.parent = parent
        self.Push()
        self.settings['position'] = [boundingRect.x() - 25, boundingRect.y() - 70]
        self.proxy.setPos(QPoint(*self.settings['position']))
        self.SetRect()
        self.ToggleStyling(active = False)
        
    def Push(self):
        super().Push()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.layout().setContentsMargins(12, 5, 12, 5)
        self.content = QWidget()
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content.setLayout(QVBoxLayout())
        self.content.layout().setContentsMargins(0, 0, 0, 0)
        self.widget.layout().addWidget(self.content)
        self.proxy.setWidget(self)
        self.proxy.setZValue(-100)

    def BaseStyling(self):
        super().BaseStyling()
        self.widget.setStyleSheet(style.WidgetStyle(color = '#6A7062', borderRadiusBottomLeft = 10, borderRadiusBottomRight = 10, borderRadiusTopRight = 10))
        self.content.setStyleSheet(style.WidgetStyle(color = '#1a1a1a', borderRadius = 8))