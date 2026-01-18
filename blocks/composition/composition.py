from PySide6.QtWidgets import QWidget, QGraphicsProxyWidget, QLineEdit, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QTimer
import asyncio
import numpy as np
from ..draggable import Draggable
from ..pv import PV
from ..kernels.kernel import Kernel
from ..filters.filter import Filter
from ...ui.runningcircle import RunningCircle
from ...utils import commands
from ... import style
from ... import shared

class Composition(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            proxy, name = kwargs.pop('name', 'Composition'), type = kwargs.pop('type', 'Composition'),
            size = kwargs.pop('size', [300, 300]), headerColor = '#D42F45', **kwargs
            )
        self.fundamental = False
        self.parent = parent
        self.blockType = 'Add'
        self.runningCircle = RunningCircle()
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(5, 5, 5, 5)
        self.widget.layout().setSpacing(5)
        self.Push()

    def Push(self):
        super().Push()
        self.main.layout().addWidget(self.widget)
        self.AddSocket('out', 'M')
        self.ToggleStyling(active = False)

    def AddLinkIn(self, ID, socket, ignoreForFirstTime = False, **kwargs):
        newFundamentalType = self.GetType(ID)
        for linkID in self.linksIn:
            existingFundamentalType = self.GetType(linkID)
            if linkID != ID:
                if existingFundamentalType == newFundamentalType:
                    break
                elif existingFundamentalType in [PV, Kernel] and newFundamentalType in [Filter, Composition]:
                    break
                elif newFundamentalType in [PV, Kernel] and existingFundamentalType in [Filter, Composition]:
                    break
                shared.workspace.assistant.PushMessage('Add operation must be performed on blocks of the same type.', 'Warning')
                return False

        successfulConnection = super().AddLinkIn(ID, socket)

        # Modify the widget based on the input type - only if this is the first of its kind.
        if successfulConnection: # and not ignoreForFirstTime:
            numLinksIn = len(self.linksIn)
            # 1. Kernel
            if numLinksIn == 1:
                deleteAndRedraw = False
                if not ignoreForFirstTime and (isinstance(shared.entities[ID], Kernel) or newFundamentalType == Kernel):
                    deleteAndRedraw = True
                    proxy, newAdd = commands.CreateBlock(self.__class__, self.name, self.proxy.pos(), size = [350, 295])
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
            self.settings.pop('hyperparameters')
            commands.CreateBlock(self.__class__, self.name, self.proxy.pos(), size = [250, 100])
            shared.activeEditor.area.selectedItems = [self.proxy,]
            commands.Delete()

    def ChangeEdit(self):
        try:
            value = float(self.edit.text())
        except:
            return
        editIdx = self.main.layout().indexOf(self.edit)
        self.main.layout().removeWidget(self.edit)
        self.edit.deleteLater()
        newEdit = QLineEdit(f'{value:.3f}')
        newEdit.setFixedSize(100, 40)
        newEdit.setAlignment(Qt.AlignCenter)
        newEdit.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 14))
        newEdit.returnPressed.connect(self.ChangeEdit)
        self.edit = newEdit
        self.widget.layout().insertWidget(editIdx, newEdit, alignment = Qt.AlignCenter)
        self.settings['threshold'] = value

    def PushKernel(self):
        self.Start = lambda: self.KernelStart()
        hyperparameters = dict()
        for ID in self.linksIn:
            for nm, val in shared.entities[ID].settings['hyperparameters'].items():
                hyperparameters[f'{nm} ({shared.entities[ID].name})'] = val
        self.settings['hyperparameters'] = hyperparameters
        self.kernel = Kernel(self, self.proxy, hyperparameters = hyperparameters)
        self.kernel.Push()
        self.kernel.k = self.k
        self.widget.layout().addWidget(self.kernel.canvas)
        self.ToggleStyling(active = False)

    def UpdateFigure(self):
        # Update the kernel function to include new kernel & redraw
        self.kernel.k = self.k
        self.kernel.UpdateFigure()
        # trigger updates in any downstream blocks attached to this that display visual information.
        for ID in self.linksOut:
            if callable(getattr(shared.entities[ID], 'UpdateFigure', None)):
                shared.entities[ID].UpdateFigure()

    def CheckState(self):
        pass

    def BaseStyling(self):
        super().BaseStyling()
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadiusBottomLeft = 8, borderRadiusBottomRight = 8))