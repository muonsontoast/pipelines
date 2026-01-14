from PySide6.QtWidgets import QGraphicsProxyWidget
from PySide6.QtCore import QTimer
import matplotlib.style as mplstyle
mplstyle.use('fast')
from .composition import Composition
from ..draggable import Draggable
from ..kernels.kernel import Kernel
from ...utils import commands
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

    def AddLinkIn(self, ID, socket, ignoreForFirstTime = False, **kwargs):
        for linkID in self.linksIn:
            if linkID != ID:
                # check if both inputs are identical types - PVs
                if type(shared.entities[ID]) == type(shared.entities[linkID]):
                    break
                # composition blocks / kernel blocks, etc. (objects with a super class below Draggable).
                elif shared.entities[ID].__class__.__base__ == shared.entities[linkID].__class__.__base__:
                    break
                else:
                    shared.workspace.assistant.PushMessage('Add operation must be performed on blocks of the same type.', 'Warning')
                    return False

        successfulConnection = super().AddLinkIn(ID, socket)

        # Modify the widget based on the input type - only if this is the first of its kind.
        if successfulConnection and not ignoreForFirstTime:
            numLinksIn = len(self.linksIn)
            # 1. Kernel
            if numLinksIn == 1:
                if isinstance(shared.entities[ID], Kernel):
                    proxy, newAdd = commands.CreateBlock(commands.blockTypes['Multiply'], self.name, self.proxy.pos(), size = [352, 275])
                    for linkID, link in self.linksIn.items():
                        newAdd.AddLinkIn(linkID, link['socket'], ignoreForFirstTime = True)
                        shared.entities[linkID].AddLinkOut(newAdd.ID, link['socket'])
                    for linkID, link in self.linksOut.items():
                        newAdd.AddLinkOut(linkID, link['socket'])
                        shared.entities[linkID].AddLinkIn(newAdd.ID, link['socket'])
                shared.activeEditor.area.selectedItems = [self.proxy,]
                QTimer.singleShot(0, commands.Delete)

        if not self.hasBeenPushed:
            if isinstance(shared.entities[next(iter(self.linksIn))], Kernel):
                self.PushKernel()
        else:
            self.UpdateFigure()

        self.hasBeenPushed = True

        return successfulConnection
    
    def RemoveLinkIn(self, ID):
        super().RemoveLinkIn(ID)
        if len(self.linksIn) > 0:
            if isinstance(shared.entities[next(iter(self.linksIn))], Kernel):
                self.kernel.RedrawFigure()
        else:
            commands.CreateBlock(commands.blockTypes['Multiply'], self.name, self.proxy.pos(), size = [250, 100])
            shared.activeEditor.area.selectedItems = [self.proxy,]
            commands.Delete()
    
    async def Start(self):
        pass
    
    async def PVStart(self):
        result = 0
        for ID in self.linksIn:
            result += await shared.entities[ID].Start()
        self.data[1] = result
        return self.data[1]
    
    async def k(self, X1, X2):
        result = 1
        for ID in self.linksIn:
            result *= await shared.entities[ID].k(X1, X2)
        return result
    
    def PushKernel(self):
        self.Start = lambda: self.KernelStart()
        hyperparameters = dict()
        for ID in self.linksIn:
            for nm, val in shared.entities[ID].settings['hyperparameters'].items():
                hyperparameters[f'{nm} ({shared.entities[ID].name})'] = val
        self.kernel = Kernel(self, self.proxy, hyperparameters = hyperparameters)
        self.kernel.Push()
        self.kernel.k = self.k
        self.widget.layout().addWidget(self.kernel.canvas)
        self.ToggleStyling(active = False)

    def UpdateFigure(self):
        # Update the kernel function to include new kernel & redraw
        self.kernel.k = self.k
        self.kernel.RedrawFigure()