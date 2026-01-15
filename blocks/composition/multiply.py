from PySide6.QtWidgets import QGraphicsProxyWidget
import matplotlib.style as mplstyle
mplstyle.use('fast')
from .composition import Composition
from ..draggable import Draggable
from ...utils.entity import Entity
from ... import shared

class Multiply(Composition):
    '''Add composition block.'''
    def __init__(self, parent: Entity, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(parent, proxy, name = kwargs.pop('name', 'Multiply'), type = 'Multiply', size = kwargs.pop('size', [250, 100]), **kwargs)
        self.hasBeenPushed = False
    
    def Push(self):
        super().Push()
        self.AddSocket('in', 'F', acceptableTypes = [Draggable])
    
    async def Start(self):
        result = 1
        for ID in self.linksIn:
            result *= await shared.entities[ID].Start()
        self.data = result
        return self.data
    
    async def k(self, X1, X2):
        result = 1
        for ID in self.linksIn:
            result *= await shared.entities[ID].k(X1, X2)
        return result