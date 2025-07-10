import os, yaml
from pathlib import Path
from . import shared
# All GUI entities do/will have a method for loading and saving their state.
cwd = str(Path.cwd().resolve()) # Get the current working directory.

class Entity:
    '''Generic class representing interactable entities in the app such as PVs and widgets.'''
    def __init__(self, name, type, ID, **kwargs):
        self.name = name # name of this entity
        self.type = type # what type of entity is this?
        self.ID = ID # unique global identifier
        for k, v in kwargs.items(): # Assign entity-specific attributes
            setattr(self, k, v)

    def __str__(self):
        s = ''
        s += self.name + '\n\n'
        s += f'ID: {self.ID}\n'
        s += f'Type: {self.type}\n'

        return s
    
def RemoveEntity(entity):
    '''Remove an existing entity from the global dataset.'''
    ID = entity.ID
    shared.entities.pop(ID, None) # will not fail if the ID does not exist.
    del entity # delete the entity

def AddEntity(entity):
    '''Add a new entity to the global dataset.'''
    shared.entities[entity.ID] = entity

def AssignEntityID():
    '''Assign a unique gloabl ID.'''
    ID = 0
    for _ID in sorted(shared.entities):
        if _ID == ID:
            ID += 1
        else:
            break
    return ID

def LoadEntities():
    '''Load the global dataset of entities.'''
    settingsExist = os.path.exists(cwd + '\\settings.yaml')

    if settingsExist:
        with open('settings.yaml', 'r') as f:
            settings = yaml.safe_load(f)
        return settings
    else:
        return dict()

def SaveEntities():
    '''Save the global dataset of entities.'''
    with open('settings.yaml', 'w') as f:
        yaml.dump(shared.entities, f)