import os
import gc
import yaml
import numpy as np
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
            for k in entitySettings:
                if k == 'components':
                    entitySettings['components'] = FormatComponents(entitySettings['components'])
                elif k == 'linkedElement':
                    entitySettings['linkedElement'] = int(entitySettings['linkedElement'].Index) # linked element can be recovered from its index next session.
                elif k == 'hyperparameters':
                    entitySettings['hyperparameters'] = FormatHyperparameters(entitySettings['hyperparameters'])
            if entitySettings['type'] == 'Editor':
                entitySettings['positionInSceneCoords'] = [entity.positionInSceneCoords.x(), entity.positionInSceneCoords.y()]
            settings[entity.ID] = entitySettings
            if entity.sharingData:
                entity.CleanUp() # remove the shared memory data from memory to stop persistance.
        gc.collect()
        yaml.dump(settings, f)
        print('Dumped session settings to disk.')

def FormatComponents(components: dict):
    newComponents = dict()
    for k, c in components.items():
        # go through and convert any numpy types to native python types for serialization.
        for attr, v in c.items():
            if isinstance(v, np.floating):
                print(f'Converting {attr} from numpy float to native float.')
                c[attr] = float(v)
            elif isinstance(v, np.integer):
                print(f'Converting {attr} from numpy int to native int.')
                c[attr] = int(v)
        newComponents[k] = c
        if 'type' in newComponents[k]:
            newComponents[k]['type'] = f'{newComponents[k]['type']}'.split('.')[-1][:-2]
        if 'valueType' in c.keys():
            if newComponents[k]['valueType'] in [int, np.integer]:
                newComponents[k]['valueType'] = 'int'
            elif newComponents[k]['valueType'] in [float, np.floating]:
                newComponents[k]['valueType'] = 'float'
            elif newComponents[k]['valueType'] == str:
                newComponents[k]['valueType'] = 'str'
    return newComponents

def FormatHyperparameters(hyperparameters: dict):
    newHyperparams = dict()
    for k, v in hyperparameters.items():
        if v['type'] == 'vec':
            if type(v['value']) == np.ndarray:
                v['value'] = v['value'].tolist()
            elif type(v['value']) in [int, float]:
                v['value'] = [v['value']]
            else:
                v['value'] = []
        newHyperparams[k] = v
    return newHyperparams