from .. import shared

class Entity:
    '''Generic class representing interactable entities in the app such as PVs and widgets.'''
    def __init__(self, *args, **kwargs): # args mostly to be compatible with other inherited classes.
        '''`entity` should be a *Draggable*-type block inside the editor, or a widget in the app.\n
        Accepts `name` and `type` overrides.'''
        super().__init__()
        self.name = kwargs.get('name', 'Entity')
        self.type = kwargs.get('type', 'Entity')
        self.settings = dict(name = self.name, type = self.type)
        for k, v in kwargs.items(): # Assign entity-specific attributes.
            if k == 'overrideID':
                continue
            self.settings[k] = v
        # Some special widgets like the inspector are exempt as they should have expanding size policies.
        if self.type not in ['Inspector'] and 'size' in kwargs.keys():
            # if 
            print(f'setting {self.name} size to {kwargs.get('size')}')
            self.setFixedSize(*kwargs.get('size'))
        self.Register(kwargs.get('overrideID')) # register this entity inside the shared.py script.

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

    def __str__(self):
        s = ''
        s += '*' + self.name + '*\n'
        s += f'ID: {self.ID}\n'
        s += f'Type: {self.type}\n'
        return s

def AssignEntityID():
    '''Assign a unique gloabl ID.'''
    ID = 0
    for _ID in sorted(shared.entities):
        if _ID == ID:
            ID += 1
        else:
            break
    return ID