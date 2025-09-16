from PySide6.QtCore import QPoint, QTimer
import os
import yaml
import time
import multiprocessing
from .commands import blockTypes, CreateBlock
from ..lattice.latticeutils import LoadLattice, GetLatticeInfo
from ..components import BPM, errors, kickangle, link, slider
from .. import shared

settings = None
t = None
componentsLookup = {
    'LinkComponent': link.LinkComponent,
    'KickAngleComponent': kickangle.KickAngleComponent,
    'ErrorsComponent': errors.ErrorsComponent,
    'BPMComponent': BPM.BPMComponent,
    'SliderComponent': slider.SliderComponent,
}
valueTypeLookup = {
    'int': int,
    'float': float,
}

def UpdateLinkedLatticeElements():
    for entity in shared.entities.values():
        if 'components' in entity.settings:
            if 'value' in entity.settings['components']:
                if entity.settings['components']['value']['type'] == slider.SliderComponent:
                    entity.UpdateLinkedElement(override = entity.settings['components']['value']['value'])
    

# Have to loop over entities again as they won't all be added before the prior loop.
def LinkBlocks():
    global settings
    for ID, v in settings.items():
        if v['type'] in blockTypes.keys():
            for sourceID, socket in v['linksIn'].items():
                shared.entities[ID].AddLinkIn(sourceID, socket)
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
            settings = yaml.safe_load(f)
            # Force an update to the editor before drawing anything to the scene.
            for v in settings.values():
                if v['type'] == 'Editor':
                    editorSettings = v
                    break
            def PopulateScene():
                for ID, v in settings.items():
                    # Populate scene blocks
                    if v['type'] in blockTypes.keys():
                        '''Block type, name, position, size, (optional) override ID.'''
                        proxy, entity = CreateBlock(
                            blockTypes[v['type']], 
                            v['name'], 
                            QPoint(v['position'][0], v['position'][1]), 
                            ID
                        )
                        entity.settings['size'] = v['size']
                        if 'alignment' in v:
                            entity.settings['alignment'] = v['alignment']
                        entity.setFixedSize(*v['size'])
                        if 'linkedElement' in v:
                            if shared.elements is None: # fetch lattice info if this is the first time instantiating a linked block.
                                shared.lattice = LoadLattice(shared.latticePath)
                                shared.elements = GetLatticeInfo(shared.lattice)
                                shared.names = [a + f' [{shared.elements.Type[b]}] ({str(b)})' for a, b in zip(shared.elements.Name, shared.elements.Index)]
                            entity.settings['linkedElement'] = shared.elements.iloc[v['linkedElement']]
                            # Assign the correct components
                            for componentName, c in v['components'].items():
                                v['components'][componentName]['type'] = componentsLookup[c['type']]
                                if 'valueType' in v['components'][componentName]:
                                    v['components'][componentName]['valueType'] = valueTypeLookup[v['components'][componentName]['valueType']]
                            entity.settings['components'] = v['components']
                LinkBlocks()
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
        shared.workspace.assistant.PushMessage(f'No saved session found.')