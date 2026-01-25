from PySide6.QtWidgets import QGraphicsProxyWidget
import matplotlib.style as mplstyle
mplstyle.use('fast')
from threading import Thread
from .composition import Composition
from ..draggable import Draggable
from ...utils.entity import Entity
from ... import shared

class Add(Composition):
    '''Add composition block.'''
    def __init__(self, parent: Entity, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(parent, proxy, name = kwargs.pop('name', 'Add'), type = 'Add', size = kwargs.pop('size', [250, 100]), **kwargs)
        self.hasBeenPushed = False
    
    def Push(self):
        super().Push()
        self.AddSocket('in', 'F', acceptableTypes = [Draggable])
    
    # def Start(self):
    #     result = 0
    #     for ID in self.linksIn:
    #         result += shared.entities[ID].Start()
    #     self.data = result
    #     return self.data

    def Start(self):
        result, threads = [], []
        for ID in self.linksIn:
            res = 0
            def StartLinkIn(_ID, res):
                res = shared.entities[ID].Start()
            result.append(res)
            t = Thread(target = StartLinkIn, args = (ID, res), daemon = True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        result = sum(result)
        self.data = result
        return self.data
    
    async def k(self, X1, X2):
        result = 0
        for ID in self.linksIn:
            result += await shared.entities[ID].k(X1, X2)
        return result