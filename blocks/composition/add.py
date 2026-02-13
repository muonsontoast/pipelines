from PySide6.QtWidgets import QGraphicsProxyWidget
import matplotlib.style as mplstyle
mplstyle.use('fast')
from threading import Thread
import numpy as np
from ..pv import PV
from ..kernels.kernel import Kernel
from .composition import Composition
from ..draggable import Draggable
from ...utils.entity import Entity
from ... import shared

class Add(Composition):
    '''Add composition block.'''
    def __init__(self, parent: Entity, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(parent, proxy, name = kwargs.pop('name', 'Add'), type = 'Add', size = kwargs.pop('size', [250, 100]), **kwargs)
        self.hasBeenPushed = False
        self.CreateEmptySharedData(np.empty(2))
        Thread(target = self.CheckValue, daemon = True).start()
    
    def Push(self):
        super().Push()
        self.AddSocket('in', 'F', acceptableTypes = [Draggable])

    def Start(self):
        with self.lock:
            self.valueRequest.set()
        self.valueReady.wait()
        with self.lock:
            self.valueRequest.clear()
            self.valueReady.clear()
        return self.data[1]
    
    def CheckValue(self):
        '''Periodically computes this block\'s value.'''
        returnNewValue = False
        while True:
            if self.stopCheckThread.is_set():
                break
            if len(self.linksIn) > 0:
                if not isinstance(next(iter(self.linksIn)), (Kernel)):
                    if hasattr(self, 'edit'):
                        try:
                            with self.lock:
                                if self.valueRequest.is_set():
                                    returnNewValue = True
                            result = np.sum([shared.entities[ID].Start() for ID in self.linksIn])
                            self.edit.setText(f'{result:.3f}') if not (np.isinf(result) or np.isnan(result)) else self.edit.setText('N/A')
                            self.data[1] = result
                        except:
                            pass
                        with self.lock:
                            if returnNewValue:
                                self.valueReady.set()
                        returnNewValue = False
            else:
                if hasattr(self, 'edit'):
                    self.edit.setText('N/A')
            self.stopCheckThread.wait(timeout = .2)
    
    def k(self, X1, X2):
        result = 0
        for ID in self.linksIn:
            result += shared.entities[ID].k(X1, X2)
        return result