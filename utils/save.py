import os
import gc
import yaml
import numpy as np
from copy import deepcopy
from .multiprocessing import runningActions, workers
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
            # tell check threads to stop
            if entity.sharingData:
                entity.stopCheckThread.set()
                try:
                    if hasattr(entity, 'inQueue') and entity.inQueue is not None:
                        entity.inQueue.close()
                    if hasattr(entity, 'outQueue') and entity.outQueue is not None:
                        entity.outQueue.close()
                except: pass
        yaml.dump(settings, f)
        print('Dumped session settings to disk.')
        # necessary to prevent leaked semaphores after close on Linux/MacOS
        runningActions.clear()
        workers.clear()
        # avoids leaked semaphores on Linux/MacOS
        for entity in shared.entities.values():
            if entity.sharingData and entity.checkThread is not None:
                try:
                    entity.checkThread.join()
                except: pass # closed itself
        # close and unlink shared memory pools
        for entity in shared.entities.values():
            if entity.sharingData:
                entity.dataSharedMemory.close()
                entity.dataSharedMemory.unlink()
                del entity.dataSharedMemory
        gc.collect()
        print('Cleaned up.')

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
        if type(v['value']) == np.ndarray:
            v['value'] = v['value'].tolist()
        elif type(v['value']) in [int, float]:
            v['value'] = v['value']
        newHyperparams[k] = v
    return newHyperparams