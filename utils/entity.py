from multiprocessing.shared_memory import SharedMemory
import numpy as np
from .. import shared

class Entity:
    '''Generic class representing interactable entities in the app such as PVs and widgets.'''
    def __init__(self, *args, **kwargs): # args mostly to be compatible with other inherited classes.
        '''`entity` should be a *Draggable*-type block inside the editor, or a widget in the app.\n
        Accepts `name` and `type` overrides.'''
        super().__init__()
        self.name = kwargs.get('name', 'Entity')
        self.type = kwargs.get('type', 'Entity')
        # self.data = np.zeros((0,))
        # self.data[:] = np.inf
        self.data = np.full(1, np.inf)
        if self.type == 'SVD':
            print('At instantiation, SVD has this data:', self.data)
        # self.data = np.inf((0,))
        self.sharingData = False
        self.settings = dict(name = self.name, type = self.type)
        for k, v in kwargs.items(): # Assign entity-specific attributes.
            if k == 'overrideID':
                continue
            self.settings[k] = v
        # Some special widgets like the inspector are exempt as they should have expanding size policies.
        if self.type not in ['Inspector'] and 'size' in kwargs.keys():
            self.setFixedSize(*kwargs.get('size'))
        self.Register(kwargs.get('overrideID')) # register this entity inside the shared.py script.

    def CreateEmptySharedData(self, emptyArray: np.ndarray, attrName = 'data'):
        sharedMemoryName = f'{attrName}SharedMemory'
        setattr(self, sharedMemoryName, SharedMemory(create = True, size = emptyArray.nbytes))
        setattr(self, attrName, np.ndarray(emptyArray.shape, dtype = emptyArray.dtype, buffer = getattr(self, sharedMemoryName).buf))
        self.sharingData = True
    
    def CleanUp(self):
        # remove the data from memory to stop it persisting after closing the application.
        self.dataSharedMemory.close()
        self.dataSharedMemory.unlink()

    def Register(self, overrideID = None):
        '''Registers this object as an entity inside the shared entity list.'''
        self.ID = overrideID
        if not overrideID:
            self.ID = AssignEntityID()  # unique global identifier
        print('Registering', self.name, 'with ID:', self.ID)
        shared.entities[self.ID] = self

    def Remove(self):
        print(f'Removing and deleting {self.name}, ID: {self.ID} from the shared entity list.')
        shared.entities.pop(self.ID, None) # will not fail if the ID does not exist.
        del self # delete this object

    def __str__(self) -> str:
        s = ''
        s += '*' + self.name + '*\n'
        s += f'ID: {self.ID}\n'
        s += f'Type: {self.type}\n'
        return s

def AssignEntityID() -> int:
    '''Assign a unique gloabl ID.'''
    ID = 0
    for _ID in sorted(shared.entities):
        if _ID == ID:
            ID += 1
        else:
            break
    return ID