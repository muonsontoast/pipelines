from PySide6.QtWidgets import QGraphicsProxyWidget, QLineEdit
from PySide6.QtCore import Qt, QTimer
import matplotlib.style as mplstyle
mplstyle.use('fast')
import asyncio
import numpy as np
from .composition import Composition
from ..draggable import Draggable
from ..kernels.kernel import Kernel
from ..filters.filter import Filter
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
        print('adding link up here to', self.name, 'with ID', self.ID, 'from', shared.entities[ID].name)
        newFundamentalType = self.GetType(ID)
        for linkID in self.linksIn:
            existingFundamentalType = self.GetType(linkID)
            if linkID != ID:
                print('existing type:', existingFundamentalType)
                print('new type:', newFundamentalType)
                if existingFundamentalType == newFundamentalType or (existingFundamentalType in [Filter, Composition] and newFundamentalType in [Filter, Composition]):
                    print('Good!')
                    break
                # check if both inputs are identical types - PVs
                # if newType == existingType:
                #     break
                # treat filter and composition of blocks like blocks
                # else:
                #     existingBase = shared.entities[linkID].__class__.__base__
                #     newBase = shared.entities[ID].__class__.__base__
                #     if existingBase in [Filter, Composition] and newBase in [Filter, Composition]:
                #         existingType, newType = self.GetType(linkID), self.GetType(ID)
                #         if existingType == newType:
                #             break
                #         # new empty
                #         elif existingType in [PV, Kernel] and newType not in [PV, Kernel]:
                #             break
                #         # existing empty
                #         elif newType in [PV, Kernel] and existingType not in [PV, Kernel]:
                #             break
                #         # both empty
                #         elif existingType not in [PV, Kernel] and newType not in [PV, Kernel]:
                #             break
                shared.workspace.assistant.PushMessage('Add operation must be performed on blocks of the same type.', 'Warning')
                return False

        successfulConnection = super().AddLinkIn(ID, socket)
        print(f'succes?', successfulConnection)
        print('********')

        # Modify the widget based on the input type - only if this is the first of its kind.
        if successfulConnection: # and not ignoreForFirstTime:
            numLinksIn = len(self.linksIn)
            # 1. Kernel
            if numLinksIn == 1:
                deleteAndRedraw = False
                if not ignoreForFirstTime and (isinstance(shared.entities[ID], Kernel) or newFundamentalType == Kernel):
                    deleteAndRedraw = True
                    proxy, newAdd = commands.CreateBlock(commands.blockTypes['Add'], self.name, self.proxy.pos(), size = [352, 275])
                    for linkID, link in self.linksIn.items():
                        newAdd.AddLinkIn(linkID, link['socket'], ignoreForFirstTime = True)
                        shared.entities[linkID].AddLinkOut(newAdd.ID, link['socket'])
                    for linkID, link in self.linksOut.items():
                        newAdd.AddLinkOut(linkID, link['socket'])
                        shared.entities[linkID].AddLinkIn(newAdd.ID, link['socket'])
                elif isinstance(shared.entities[ID], PV):
                    deleteAndRedraw = True
                    # add a line edit element
                    self.edit = QLineEdit()
                    self.edit.setFixedSize(100, 40)
                    self.edit.setAlignment(Qt.AlignCenter)
                    self.edit.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 14))
                    self.edit.returnPressed.connect(self.ChangeEdit)
                    self.edit.setReadOnly(True)
                    self.widget.layout().addWidget(self.edit, alignment = Qt.AlignCenter)
                    self.timerRunning = True
                    async def FetchValues():
                        # this QTimer can run after deleting last PV so explicitly check if PVs are still linked.
                        if len(self.linksIn) > 0:
                            result = await self.Start()
                            result = 'N/A' if np.isnan(result) else f'{result:.3f}'
                            self.edit.setText(result)
                            QTimer.singleShot(100, lambda: asyncio.create_task(FetchValues()))
                    asyncio.create_task(FetchValues())

                if deleteAndRedraw:
                    shared.activeEditor.area.selectedItems = [self.proxy,]
                    QTimer.singleShot(0, commands.Delete)
                else:
                    if newFundamentalType == Kernel:
                        if not self.hasBeenPushed:
                            self.PushKernel()
            else:
                if newFundamentalType == Kernel:
                    self.UpdateFigure()

        self.hasBeenPushed = True
        return successfulConnection
    
    def RemoveLinkIn(self, ID):
        super().RemoveLinkIn(ID)
        if len(self.linksIn) > 0:
            if isinstance(shared.entities[next(iter(self.linksIn))], Kernel):
                self.kernel.RedrawFigure()
        else:
            self.timerRunning = False
            commands.CreateBlock(commands.blockTypes['Add'], self.name, self.proxy.pos(), size = [250, 100])
            shared.activeEditor.area.selectedItems = [self.proxy,]
            commands.Delete()
    
    async def Start(self):
        result = 0
        for ID in self.linksIn:
            result += await shared.entities[ID].Start()
        self.data = result
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
        # trigger updates in any downstream blocks attached to this that display visual information.
        for ID in self.linksOut:
            if callable(getattr(shared.entities[ID], 'UpdateFigure', None)):
                shared.entities[ID].UpdateFigure()