import os
import yaml
from copy import deepcopy
from .. import shared

def Save():
    path = os.path.join(shared.cwd, 'config')
    if not os.path.exists(path):
        print('Config folder does not exist. Creating one.')
        os.mkdir(path)
    with open(os.path.join(path, 'settings.yaml'), 'w') as f:
        settings = dict()
        for entity in shared.entities.values():
            entitySettings = deepcopy(entity.settings)
            # Replace settings of specific kinds with more appropriate information.
            for k in entitySettings.keys():
                if k == 'components':
                    entitySettings['components'] = FormatComponents(entitySettings['components'])
                elif k == 'linkedElement':
                    entitySettings['linkedElement'] = int(entitySettings['linkedElement'].Index) # linked element can be recovered from its index next session.
            if entitySettings['type'] == 'Editor':
                entitySettings['positionInSceneCoords'] = [entity.positionInSceneCoords.x(), entity.positionInSceneCoords.y()]
            settings[entity.ID] = entitySettings
            if entity.sharingData:
                entity.CleanUp() # remove the shared memory data from memory to stop persistance.
                print(f'Finished cleaning up data from {entity.name}')
        yaml.dump(settings, f)
        print('Dumped session settings to disk.')

def FormatComponents(components: dict):
    newComponents = dict()
    for k, c in components.items():
        newComponents[k] = c
        newComponents[k]['type'] = f'{newComponents[k]['type']}'.split('.')[-1][:-2]
        if 'valueType' in c.keys():
            if newComponents[k]['valueType'] == int:
                newComponents[k]['valueType'] = 'int'
            elif newComponents[k]['valueType'] == float:
                newComponents[k]['valueType'] = 'float'
            elif newComponents[k]['valueType'] == str:
                newComponents[k]['valueType'] = 'str'
    return newComponents