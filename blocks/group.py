from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget
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
            size = kwargs.pop('size', [int(boundingRect.width()) + 150, int(boundingRect.height()) + 100]),
            headerColor = "#6A7062",
            numBlocks = numBlocks,
            IDs = IDs,
            showing = kwargs.pop('showing', True),
            **kwargs
        )
        for ID in IDs:
            shared.entities[ID].groupID = self.ID # inform blocks that they belong to this group.
        self.groupBlocks.append(self)
        self.parent = parent
        self.Push()
        self.settings['position'] = [boundingRect.x() - 75, boundingRect.y() - 70]
        self.proxy.setPos(QPoint(*self.settings['position']))
        self.SetRect()
        # Add external links of children to the sockets of the group.
        for block in self.groupBlocks:
            for ID in block.linksIn:
                if ID not in self.settings['IDs'] and ID not in self.linksIn:
                    self.AddLinkIn(ID, 'in', Z = -101, hide = True)
                    shared.entities[ID].AddLinkOut(self.ID, 'in')
            for ID, socket in block.linksOut.items():
                if ID == 'free':
                    continue
                if ID not in self.settings['IDs'] and ID not in self.linksOut:
                    shared.entities[ID].AddLinkIn(self.ID, socket, Z = -101, hide = True)
                    self.AddLinkOut(ID, socket)
        self.ToggleStyling(active = False)
        shared.activeEditor.scene.update()
        
    def Push(self):
        super().Push()
        self.AddSocket('in', 'F', acceptableTypes = [Draggable])
        self.AddSocket('out', 'M')
        self.inSocket.hide()
        self.outSocket.hide()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.layout().setContentsMargins(12, 5, 12, 5)
        self.content = QWidget()
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content.setLayout(QVBoxLayout())
        self.content.layout().setContentsMargins(5, 5, 5, 5)
        self.label = QLabel('WOW')
        self.label.hide()
        self.content.layout().addWidget(self.label, alignment = Qt.AlignTop)
        self.widget.layout().addWidget(self.content)
        self.proxy.setWidget(self)
        self.proxy.setZValue(-100)

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
        super().BaseStyling()
        self.widget.setStyleSheet(style.WidgetStyle(color = '#6A7062', borderRadiusBottomLeft = 10, borderRadiusBottomRight = 10, borderRadiusTopRight = 10))
        self.content.setStyleSheet(style.WidgetStyle(color = '#1a1a1a', borderRadius = 8))