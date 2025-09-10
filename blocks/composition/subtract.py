from PySide6.QtWidgets import QGraphicsProxyWidget
from PySide6.QtCore import QTimer, Signal
import numpy as np
from .composition import Composition
from ..socket import Socket
from ...actions.action import Action
from ...utils.entity import Entity
from ... import style
from ... import shared

class Subtract(Composition):
    '''Subtract composition block.'''
    def __init__(self, parent: Entity, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(parent, proxy, name = kwargs.pop('name', 'Subtract'), type = 'Subtract', size = [300, 150], **kwargs)
        self.A, self.B = None, None
        self.streams = {
            'result': lambda: {
                'data': self.A.streams[self.streamTypesIn[self.A.ID]]()['data'] - self.B.streams[self.streamTypesIn[self.B.ID]]()['data']
            }
        }
        self.action = Action(self)
        self.aSocket = Socket(self, 'F', 50, 25, 'left', 'a', acceptableTypes = ['PV', 'Corrector', 'BPM', 'BCM', 'Single Task GP'])
        self.bSocket = Socket(self, 'F', 50, 25, 'left', 'b', acceptableTypes = ['PV', 'Corrector', 'BPM', 'BCM', 'Single Task GP'])
        self.FSocketWidgets.layout().removeWidget(self.inSocket)
        self.inSocket.setParent(None)
        self.inSocket.deleteLater()
        del self.inSocket
        self.FSocketWidgets.layout().addWidget(self.aSocket)
        self.FSocketWidgets.layout().addWidget(self.bSocket)
        self.FSocketNames = ['a', 'b']
        self.Push()

    def Push(self):
        self.ToggleStyling(active = False)

    def Start(self, downstreamData:np.ndarray = None):
        '''Data can be either targets or actionData, depending on which input of the downstream block this is attached to.'''
        self.resultsWritten = False
        # dependents to be deprecated in a future version
        self.action.ReadDependents(
        [
            {'ID': self.A.ID, 'stream': self.streamTypesIn[self.A.ID]},
            {'ID': self.B.ID, 'stream': self.streamTypesIn[self.B.ID]},
        ],
        downstreamData)
        
        def Wait():
            if not self.action.resultsWritten:
                return QTimer.singleShot(self.timeBetweenPolls, Wait)
            self.action.resultsWritten = False
            self.resultsWritten = True
        Wait()

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.main.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 20))
        super().BaseStyling()

    def SelectedStyling(self):
        pass

    def AddLinkIn(self, ID, socket):
        # don't allow multiple links to the same socket
        for linkID, link in self.linksIn.items():
            if linkID != ID and link['socket'] == socket:
                self.RemoveLinkIn(linkID)
                shared.entities[linkID].RemoveLinkOut(self.ID)
                break
        super().AddLinkIn(ID, socket)
        if socket == 'a':
            self.A = shared.entities[ID]
        else:
            self.B = shared.entities[ID]

    def RemoveLinkIn(self, ID):
        if self.linksIn[ID]['socket'] == 'a':
            self.A = None
        else:
            self.B = None
        return super().RemoveLinkIn(ID)