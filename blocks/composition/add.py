from PySide6.QtWidgets import QGraphicsProxyWidget, QLineEdit
from PySide6.QtCore import Qt, QTimer
import matplotlib.style as mplstyle
mplstyle.use('fast')
import asyncio
from .composition import Composition
from ..draggable import Draggable
from ..kernels.kernel import Kernel
from ..pv import PV
from ...utils import commands
from ...utils.entity import Entity
from ... import shared
from ... import style

class Add(Composition):
    '''Add composition block.'''
    def __init__(self, parent: Entity, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(parent, proxy, name = kwargs.pop('name', 'Add'), type = 'Add', size = kwargs.pop('size', [250, 100]), **kwargs)
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
                deleteAndRedraw = True
                if isinstance(shared.entities[ID], Kernel):
                    proxy, newAdd = commands.CreateBlock(commands.blockTypes['Add'], self.name, self.proxy.pos(), size = [352, 275])
                    for linkID, link in self.linksIn.items():
                        newAdd.AddLinkIn(linkID, link['socket'], ignoreForFirstTime = True)
                        shared.entities[linkID].AddLinkOut(newAdd.ID, link['socket'])
                    for linkID, link in self.linksOut.items():
                        newAdd.AddLinkOut(linkID, link['socket'])
                        shared.entities[linkID].AddLinkIn(newAdd.ID, link['socket'])
                elif isinstance(shared.entities[ID], PV):
                    deleteAndRedraw = False
                    # add a line edit element
                    self.edit = QLineEdit()
                    self.edit.setFixedSize(100, 40)
                    self.edit.setAlignment(Qt.AlignCenter)
                    self.edit.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 14))
                    self.edit.returnPressed.connect(self.ChangeEdit)
                    self.widget.layout().addWidget(self.edit, alignment = Qt.AlignCenter)
                    asyncio.create_task(self.Start())

                if deleteAndRedraw:
                    shared.activeEditor.area.selectedItems = [self.proxy,]
                    QTimer.singleShot(0, commands.Delete)
            else:
                if isinstance(shared.entities[ID], Kernel):
                    self.PushKernel() if not self.hasBeenPushed else self.UpdateFigure()
                if isinstance(shared.entities[ID], PV):
                    asyncio.create_task(self.Start())

        self.hasBeenPushed = True
        return successfulConnection
    
    def RemoveLinkIn(self, ID):
        super().RemoveLinkIn(ID)
        if len(self.linksIn) > 0:
            if isinstance(shared.entities[next(iter(self.linksIn))], Kernel):
                self.kernel.RedrawFigure()
        else:
            commands.CreateBlock(commands.blockTypes['Add'], self.name, self.proxy.pos(), size = [250, 100])
            shared.activeEditor.area.selectedItems = [self.proxy,]
            commands.Delete()
    
    async def Start(self):
        result = 0
        for ID in self.linksIn:
            result += await shared.entities[ID].Start()
        self.data = result
        self.edit.setText(f'{self.data:.3f}')
        return self.data
    
    async def k(self, X1, X2):
        result = 0
        for ID in self.linksIn:
            result += await shared.entities[ID].k(X1, X2)
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

    def ChangeEdit(self):
        try:
            value = float(self.edit.text())
        except:
            return
        editIdx = self.widget.layout().indexOf(self.edit)
        self.widget.layout().removeWidget(self.edit)
        self.edit.deleteLater()
        newEdit = QLineEdit(f'{value:.3f}')
        newEdit.setFixedSize(100, 40)
        newEdit.setAlignment(Qt.AlignCenter)
        newEdit.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 14))
        newEdit.returnPressed.connect(self.ChangeEdit)
        self.edit = newEdit
        self.widget.layout().insertWidget(editIdx, newEdit, alignment = Qt.AlignCenter)

    def UpdateFigure(self):
        # Update the kernel function to include new kernel & redraw
        self.kernel.k = self.k
        self.kernel.RedrawFigure()