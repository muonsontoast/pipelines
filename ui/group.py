from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsProxyWidget, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from ..utils.entity import Entity
from .. import shared
from .. import style

class Group(Entity, QGraphicsRectItem):
    def __init__(self, *args:QGraphicsProxyWidget, **kwargs):
        '''`*args` is a list of child items to attach to the group.'''
        super().__init__(name = kwargs.pop('name', 'Group'), type = 'Group')
        shared.activeEditor.scene.addItem(self)
        self.padding = 10
        self.setZValue(-200)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setBrush(QColor('#242424'))
        self.setPen(Qt.NoPen)

        # calculate the bounding rect
        boundingRect = args[0].sceneBoundingRect()
        for item in args[1:]:
            boundingRect = boundingRect.united(item.sceneBoundingRect())

        self.setRect(boundingRect.x() - self.padding, boundingRect.y() - self.padding, boundingRect.width() + 2 * self.padding, boundingRect.height() + 2 * self.padding)
        for item in args:
            item.setParentItem(self)