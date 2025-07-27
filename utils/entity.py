import os, yaml
from .. import shared

class Entity:
    '''Generic class representing interactable entities in the app such as PVs and widgets.'''
    def __init__(self, entity, **kwargs):
        '''`entity` should be a *Draggable*-type block inside the editor, or a widget in the app.'''
        settingsKeys = entity.settings.keys()
        self.type = entity.settings['type'] if 'type' in settingsKeys else entity.__class__ # what type of entity is this?
        self.ID = AssignEntityID()  # unique global identifier
        # Name the entity
        if 'name' in settingsKeys:
            self.name = entity.settings['name']
        else: self.name = f'{entity.__class__}'.split('.')[-1].title()
        for k, v in kwargs.items(): # Assign entity-specific attributes
            setattr(self, k, v)
        shared.entities[self.ID] = self

    def Remove(self):
        ID = entity.ID
        shared.entities.pop(ID, None) # will not fail if the ID does not exist.
        del entity # delete the entity

    def __str__(self):
        s = ''
        s += self.name + '\n\n'
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