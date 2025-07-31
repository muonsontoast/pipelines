import os, yaml
from .. import shared

class Entity:
    '''Generic class representing interactable entities in the app such as PVs and widgets.'''
    def __init__(self, *args, **kwargs): # args mostly to be compatible with other inherited classes.
        '''`entity` should be a *Draggable*-type block inside the editor, or a widget in the app.\n
        Accepts `name` and `type` overrides.'''
        super().__init__()
        self.name = kwargs.get('name', 'Entity')
        self.type = kwargs.get('type', Entity)
        self.settings = dict(name = self.name)
        for k, v in kwargs.items(): # Assign entity-specific attributes.
            self.settings[k] = v
        if 'size' in kwargs.keys():
            self.setFixedSize(*kwargs.get('size'))
        self.Register() # register this entity inside the shared.py script.

    def Register(self):
        '''Registers this object as an entity inside the shared entity list.'''
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

# def LoadEntities():
#     '''Load the global dataset of entities.'''
#     settingsExist = os.path.exists(cwd + '\\settings.yaml')

#     if settingsExist:
#         with open('settings.yaml', 'r') as f:
#             settings = yaml.safe_load(f)
#         return settings
#     else:
#         return dict()

# def SaveEntities():
#     '''Save the global dataset of entities.'''
#     with open('settings.yaml', 'w') as f:
#         yaml.dump(shared.entities, f)