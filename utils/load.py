from PySide6.QtCore import QPoint, QTimer
import os
import yaml
import time
import multiprocessing
from pathlib import Path
import numpy as np
from .commands import blockTypes, CreateBlock, ToggleGroup
from ..blocks.composition.composition import Composition
from ..blocks.kernels.kernel import Kernel
from ..lattice.latticeutils import LoadLattice, GetLatticeInfo
from ..components import BPM, errors, kickangle, link, slider, kernel
from .. import shared

settings = None
t = None
componentsLookup = {
    'LinkComponent': link.LinkComponent,
    'KickAngleComponent': kickangle.KickAngleComponent,
    'ErrorsComponent': errors.ErrorsComponent,
    'BPMComponent': BPM.BPMComponent,
    'SliderComponent': slider.SliderComponent,
    'KernelComponent': kernel.KernelComponent,
}
valueTypeLookup = {
    'int': int,
    'float': float,
}

def UpdateHyperparameters():
    for entity in shared.entities.values():
        if 'hyperparameters' in entity.settings and len(entity.linksIn) > 0 and isinstance(shared.entities[next(iter(entity.linksIn))], Kernel):
            for hname, h in entity.settings['hyperparameters'].items():
                if h['type'] == 'vec':
                    entity.settings['hyperparameters'][hname]['value'] = np.array(h['value']) if len(h['value']) > 0 else np.nan
                    editName = f'{hname}Edit'
                    if hasattr(entity, editName):
                        getattr(entity, editName).setText(f'{entity.settings['hyperparameters'][hname]['value'][0]:.1f}')
            entity.UpdateFigure()
    print('Hyperparameters (if any) updated.')

def UpdateLinkedLatticeElements():
    for entity in shared.entities.values():
        if 'components' in entity.settings:
            if 'value' in entity.settings['components']:
                if 'type' in entity.settings['components']['value']:
                    if entity.settings['components']['value']['type'] == slider.SliderComponent:
                        if 'linkedLatticeElement' in entity.settings['components']:
                            entity.UpdateLinkedElement(override = entity.settings['components']['value']['value'])
    UpdateHyperparameters()

# Have to loop over entities again as they won't all be added before the prior loop.
def LinkBlocks():
    global settings
    for ID, v in settings.items():
        if v['type'] == 'Group':
            for sourceID, socket in v['linksIn'].items():
                shared.entities[ID].AddLinkIn(sourceID, socket, Z = -101, hide = True, updateGroupLinks = False)
            for targetID, socket in v['linksOut'].items():
                shared.entities[ID].AddLinkOut(targetID, socket)
        elif v['type'] in blockTypes:
            for sourceID, socket in v['linksIn'].items():
                if shared.entities[sourceID].type == 'Group':
                    continue
                ignoreForFirstTime = isinstance(shared.entities[ID], Composition)
                shared.entities[ID].AddLinkIn(sourceID, socket, ignoreForFirstTime = ignoreForFirstTime, updateGroupLinks = False)
            for targetID, socket in v['linksOut'].items():
                shared.entities[ID].AddLinkOut(targetID, socket)
    UpdateLinkedLatticeElements()
    numCPUs = multiprocessing.cpu_count()
    print(f'There are {numCPUs} CPU cores available.')

def Load(path):
    '''Populate entities from a settings file held inside the config folder.'''
    global settings, t
    if os.path.exists(path):
        shared.workspace.assistant.PushMessage(f'Loading saved session from {path}')
        with open(path, 'r') as f:
            gitignore = Path(shared.cwd) / 'config' / '.gitignore'
            if not gitignore.exists():
                gitignore.write_text('# Store any settings files in this folder.')
            settings = yaml.safe_load(f)
            # Force an update to the editor before drawing anything to the scene.
            for v in settings.values():
                if v['type'] == 'Editor':
                    editorSettings = v
                    break
            def PopulateScene():
                groups = dict() # process groups separately
                for ID, v in settings.items():
                    if v['type'] == 'Group':
                        groups[ID] = v
                        shared.numGroups += 1
                        continue
                    # Populate scene blocks
                    if v['type'] in blockTypes.keys():
                        '''Block type, name, position, size, (optional) override ID.'''
                        if not 'position' in v:
                            continue
                        proxy, entity = CreateBlock(
                            blockTypes[v['type']], 
                            v['name'], 
                            QPoint(v['position'][0], v['position'][1]), 
                            ID,
                            size = v['size'],
                            automatic = v.get('automatic', None),
                            linkedPVs = v.get('linkedPVs', None),
                            acqFunction = v.get('acqFunction', None),
                            acqHyperparameter = v.get('acqHyperparameter', None),
                            numSamples = v.get('numSamples', None),
                            numSteps = v.get('numSteps', None),
                            mode = v.get('mode', None),
                            dtype = v.get('dtype', None),
                            numberValue = v.get('numberValue', None),
                            numBlocks = v.get('numBlocks', None),
                            IDs = v.get('IDs', None),
                            magnitudeOnly = v.get('magnitudeOnly', None),
                            threshold = v.get('threshold', None),
                            onControl = v.get('onControl', None),
                            hyperparameters = v.get('hyperparameters', None),
                        )
                        if 'alignment' in v:
                            entity.settings['alignment'] = v['alignment']
                        entity.setFixedSize(*v['size'])
                        if 'linkedElement' in v:
                            if shared.elements is None: # fetch lattice info if this is the first time instantiating a linked block.
                                shared.lattice = LoadLattice(shared.latticePath)
                                shared.elements = GetLatticeInfo(shared.lattice)
                                shared.names = [a + f' [{shared.elements.Type[b]}] (Index: {str(b)}) @ {shared.elements['s (m)'].iloc[b]:.2f} m' for a, b in zip(shared.elements.Name, shared.elements.Index)]
                            entity.settings['linkedElement'] = shared.elements.iloc[v['linkedElement']]
                        # Assign the correct components
                        if 'components' in v:
                            for componentName, c in v['components'].items():
                                if 'type' in v['components'][componentName]:
                                    v['components'][componentName]['type'] = componentsLookup[c['type']]
                                if 'valueType' in v['components'][componentName]:
                                    v['components'][componentName]['valueType'] = valueTypeLookup[v['components'][componentName]['valueType']]
                            entity.settings['components'] = v['components']
                            if hasattr(entity, 'set'):
                                entity.set.setText(f'{v['components']['value']['value']:.3f}')
                        # if 'hyperparameters' in v:
                        #     for h in v['hyperparameters']:
                        #         v['hyperparameters'][h]['value'] = np.array(v['hyperparameters'][h]['value'])
                        #     entity.settings['hyperparameters'] = v['hyperparameters']
                # process groups after populating the scene
                for ID, v in groups.items():
                    proxy, entity = CreateBlock(
                        blockTypes[v['type']], 
                        v['name'],
                        QPoint(v['position'][0], v['position'][1]), 
                        ID,
                        size = v['size'],
                        numBlocks = v.get('numBlocks', None),
                        IDs = v.get('IDs', None),
                        showing = v.get('showing', True),
                        note = v.get('note', ''),
                    )
                LinkBlocks()
                for ID in groups:
                    shared.entities[ID].dropdown.pressed.connect(lambda _ID = ID: ToggleGroup(shared.entities[_ID]))
                    if not shared.entities[ID].settings['showing']:
                        shared.entities[ID].settings['showing'] = True
                        ToggleGroup(shared.entities[ID])
                print(f'Previous session state loaded in {time.time() - t:.2f} seconds.')
                shared.workspace.assistant.PushMessage(f'Loaded saved session from {path}')
            def CenterEditor():
                shared.activeEditor.positionInSceneCoords = QPoint(editorSettings['positionInSceneCoords'][0], editorSettings['positionInSceneCoords'][1])
                shared.activeEditor.centerOn(shared.activeEditor.positionInSceneCoords.x(), shared.activeEditor.positionInSceneCoords.y())
                shared.activeEditor.coordsTitle.setText(f'Editor center: ({shared.activeEditor.positionInSceneCoords.x():.0f}, {shared.activeEditor.positionInSceneCoords.y():.0f})')
                QTimer.singleShot(0, PopulateScene)
            def ScaleEditor():
                shared.activeEditor.scale(editorSettings['zoom'], editorSettings['zoom'])
                shared.activeEditor.settings['zoom'] = editorSettings['zoom']
                shared.activeEditor.zoomTitle.setText(f'Zoom: {editorSettings["zoom"] * 100:.0f}%')
                QTimer.singleShot(0, CenterEditor)
            t = time.time()
            QTimer.singleShot(0, ScaleEditor)
    else:
        configPath = Path(shared.cwd) / 'config'
        if not os.path.exists(configPath):
            os.mkdir(configPath)
        (configPath / '.gitignore').write_text('# Store any custom YAML settings files in this folder.')
        shared.workspace.assistant.PushMessage(f'No saved session found.')