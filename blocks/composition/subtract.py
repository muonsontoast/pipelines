from PySide6.QtWidgets import QGraphicsProxyWidget
from PySide6.QtCore import QTimer
import numpy as np
from .composition import Composition
from ..draggable import Draggable
from ...actions.action import Action
from ...utils.entity import Entity
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

    def Push(self):
        super().Push()
        self.AddSocket('a', 'F', acceptableTypes = [Draggable])
        self.AddSocket('b', 'F', acceptableTypes = [Draggable])

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

    def AddLinkIn(self, ID, socket):
        for linkID, link in self.linksIn.items():
            if linkID != ID:
                # check if both inputs are identical types - PVs
                if type(shared.entities[ID]) == type(shared.entities[linkID]):
                    if link['socket'] == socket:
                        self.RemoveLinkIn(linkID)
                        shared.entities[linkID].RemoveLinkOut(self.ID)
                    break
                # composition blocks / kernel blocks, etc. (objects with a super class below Draggable).
                elif shared.entities[ID].__class__.__base__ == shared.entities[linkID].__class__.__base__:
                    if link['socket'] == socket:
                        self.RemoveLinkIn(linkID)
                        shared.entities[linkID].RemoveLinkOut(self.ID)
                    break
                else:
                    shared.workspace.assistant.PushMessage('Subtract operation must be performed on blocks of the same type.', 'Warning')
                    return False
        if socket == 'a':
            self.A = shared.entities[ID]
        else:
            self.B = shared.entities[ID]
        return super().AddLinkIn(ID, socket)

    def RemoveLinkIn(self, ID):
        if self.linksIn[ID]['socket'] == 'a':
            self.A = None
        else:
            self.B = None
        return super().RemoveLinkIn(ID)