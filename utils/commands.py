'''Commands performed inside the editor. Tracks undo and redo actions.'''

from PySide6.QtWidgets import QGraphicsProxyWidget, QApplication, QGraphicsScene
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import QPoint, QPointF, QRectF, QSizeF
import asyncio
import numpy as np
from copy import deepcopy
from ..blocks.draggable import Draggable
from ..blocks.pv import PV
from ..blocks.corrector import Corrector
from ..blocks.bcm import BCM
from ..blocks.bpm import BPM
from ..blocks.orbitresponse import OrbitResponse
from ..blocks.view import View
from ..blocks.save import Save as SaveBlock
from ..blocks.composition.add import Add
from ..blocks.composition.multiply import Multiply
from ..blocks.number import Number
from ..blocks.composition.svd import SVD
from ..blocks.bayesian.singletaskgp import SingleTaskGP
# kernels
from ..blocks.kernels.kernel import Kernel
from ..blocks.kernels.linear import LinearKernel
from ..blocks.kernels.anisotropic import AnisotropicKernel
from ..blocks.kernels.periodic import PeriodicKernel
from ..blocks.kernels.rbf import RBFKernel
from ..blocks.kernels.matern import MaternKernel
from ..blocks.filters.greaterthan import GreaterThan as GreaterThanFilter
from ..blocks.filters.lessthan import LessThan as LessThanFilter
from ..blocks.filters.control import Control
from ..blocks.filters.invert import Invert
from ..blocks.filters.absolute import Absolute
from ..blocks.constraints.greaterthan import GreaterThan
from ..blocks.constraints.lessthan import LessThan
from ..blocks.group import Group
from ..ui.groupmenu import GroupMenu
from .multiprocessing import TogglePause, StopActions, runningActions
from .save import Save
from .. import shared

editor = None
autosave = True

blockTypes = {
    'PV': PV,
    'Corrector': Corrector,
    'BCM': BCM,
    'BPM': BPM,
    'Orbit Response': OrbitResponse,
    'View': View,
    'Save': SaveBlock,
    'Add': Add,
    'Multiply': Multiply,
    'Number': Number,
    'SVD': SVD,
    'Single Task GP': SingleTaskGP,
    'Group': Group,
    'Group Menu': GroupMenu,
    'Kernel': Kernel,
    'Linear Kernel': LinearKernel,
    'Anisotropic Kernel': AnisotropicKernel,
    'Periodic Kernel': PeriodicKernel,
    'RBF Kernel': RBFKernel,
    'Matern Kernel': MaternKernel,
    '> (Constraint)': GreaterThan,
    '< (Constraint)': LessThan,
    '> (Filter)': GreaterThanFilter,
    '< (Filter)': LessThanFilter,
    'Control': Control,
    'Invert': Invert,
    'Absolute': Absolute,
}

maxActionBufferSize = 10 # number of consecutive actions stored
actionBuffer = [] # a list of lists, e.g. [[Paste, mousePos, blockBuffer], ...]
actionPointerIdx = 0
blockBuffer = []

def PrintBuffer(idxInItems):
    global actionBuffer, actionPointerIdx
    print('== ACTION BUFFER ==')
    print('Pointer Idx:', actionPointerIdx)
    s = ['_' for _ in range(maxActionBufferSize)]
    for _ in range(len(actionBuffer)):
        entry = actionBuffer[_][idxInItems]
        if isinstance(entry, (QPoint, QPointF)):
            s[_] = f'[{entry.x()}, {entry.y()}]'
        else:
            s[_] = entry
    print(' '.join(s))

def Undo():
    global maxActionBufferSize, actionPointerIdx
    if actionPointerIdx >= len(actionBuffer) or actionPointerIdx >= maxActionBufferSize:
        return
    actionToUndo, *args  = actionBuffer[actionPointerIdx]
    shared.workspace.assistant.ignoreRequests = True
    if actionToUndo == Paste:
        data = args[2]
        for block in shared.activeEditor.area.selectedBlocks:
            block.ToggleStyling(active = False)
        shared.activeEditor.area.selectedItems = data
        Delete()
        shared.workspace.assistant.ignoreRequests = False
        shared.workspace.assistant.PushMessage('Paste was undone.')
    actionPointerIdx += 1

def Redo():
    global maxActionBufferSize, actionPointerIdx, blockBuffer, actionBuffer
    if actionPointerIdx == 0:
        return
    actionPointerIdx -= 1
    actionToRedo, *args = actionBuffer[actionPointerIdx]
    actionBuffer.pop(actionPointerIdx)
    shared.workspace.assistant.ignoreRequests = True
    if actionToRedo == Paste:
        global blockBuffer
        mousePos, offsets, items, blocks = args
        blockBuffer = blocks
        Paste(mousePos = mousePos, offsets = offsets, modifyActionBuffer = False)
    actionBuffer.insert(actionPointerIdx, [Paste, mousePos, offsets, shared.activeEditor.area.selectedItems, blockBuffer])

def Copy():
    global blockBuffer
    blockBuffer = shared.activeEditor.area.selectedBlocks
    shared.workspace.assistant.PushMessage(f'Copied {len(shared.activeEditor.area.selectedBlocks)} block(s).')

def Paste(mousePos = None, offsets = None, modifyActionBuffer = True):
    global blockBuffer, actionBuffer, maxActionBufferSize, actionPointerIdx
    groups = dict()
    oldToNewIDs = dict()
    mousePos = GetMousePos() if mousePos is None else mousePos
    # deselect all existing selected
    for block in shared.activeEditor.area.selectedBlocks:
        block.ToggleStyling()
    # compute centre of mass
    positions = np.array([block.settings['position'] for block in blockBuffer])
    if offsets is None:
        CoM = QPoint(np.mean(positions[:, 0]), np.mean(positions[:, 1]))
        offsets = {block.ID: QPoint(*block.settings['position']) - CoM for block in blockBuffer}
    newBlocks, newItems, multipleBlocksSelected = [], [], False
    shared.workspace.assistant.ignoreRequests = True
    for block in blockBuffer:
        if block.groupID is not None:
            if block.groupID not in groups:
                groups[block.groupID] = [block.ID]
            else:
                groups[block.groupID].append(block.ID)
        proxy, entity = CreateBlock(
            blockTypes[block.type],
            block.name,
            mousePos + offsets[block.ID],
            size = block.settings['size'],
            automatic = block.settings.get('automatic', None),
            acqFunction = block.settings.get('acqFunction', None),
            acqHyperparameter = block.settings.get('acqHyperparameter', None),
            numSamples = block.settings.get('numSamples', None),
            numSteps = block.settings.get('numSteps', None),
            mode = block.settings.get('mode', None),
            dtype = block.settings.get('dtype', None),
            numberValue = block.settings.get('numberValue', None),
            numBlocks = block.settings.get('numBlocks', None),
            magnitudeOnly = block.settings.get('magnitudeOnly', None),
            threshold = block.settings.get('threshold', None),
            onControl = block.settings.get('onControl', None),
        )
        entity.settings['components'] = deepcopy(block.settings['components'])
        if hasattr(entity, 'set'):
            if 'value' in entity.settings['components']:
                entity.set.setText(f'{entity.settings['components']['value']['value']:.3f}')
        oldToNewIDs[block.ID] = entity.ID
        entity.ToggleStyling()
        # Keep the buffer the same, but change the selected blocks over to the newly pasted ones.
        newBlocks.append(entity)
        newItems.append(proxy)
    multipleBlocksSelected = True if len(newBlocks) > 1 else False
    
    for block in blockBuffer:
        # linked IDs may not be included in the paste, so remove those links by default.
        for ID, link in block.linksIn.items():
            if ID in oldToNewIDs:
                shared.entities[oldToNewIDs[block.ID]].AddLinkIn(oldToNewIDs[ID], link['socket'])
        for ID, socket in block.linksOut.items():
            if ID in oldToNewIDs:
                shared.entities[oldToNewIDs[block.ID]].AddLinkOut(oldToNewIDs[ID], socket)

    shared.activeEditor.area.selectedBlocks = newBlocks
    shared.activeEditor.area.selectedItems = newItems
    shared.activeEditor.area.multipleBlocksSelected = multipleBlocksSelected

    if multipleBlocksSelected:
        shared.inspector.PushMultiple()
    else:
        shared.selectedPV = newBlocks[0]
        shared.selected = [newBlocks[0].ID]
        shared.inspector.Push(newBlocks[0])

    if modifyActionBuffer:
        del actionBuffer[:actionPointerIdx]
        actionPointerIdx = 0
        actionBuffer.insert(0, [Paste, mousePos, offsets, newItems, blockBuffer])
        if len(actionBuffer) > maxActionBufferSize:
            actionBuffer.pop(-1)
    
    shared.workspace.assistant.ignoreRequests = False
    shared.workspace.assistant.PushMessage(f'Pasted {len(newBlocks)} block(s).')

def Snip(): # cut links
    pass

def StopAllActions():
    StopActions()

async def ToggleAllActions():
    # check which blocks can run and have well-defined inputs.
    shared.toggleState = not shared.toggleState if shared.changeToggleState else shared.toggleState
    shared.changeToggleState = True
    shared.workspace.assistant.ignoreRequests = True

    if shared.toggleState:
        allRunnableBlocksFinished = True
        for r in shared.runnableBlocks.values():
            if not r.actionFinished.is_set():
                allRunnableBlocksFinished = False
                if r.ID not in runningActions:
                    r.Start(False)
                elif runningActions[r.ID][0].is_set():
                    r.progressBar.TogglePause(False)
                    TogglePause(r, False)
        if allRunnableBlocksFinished:
            for r in shared.runnableBlocks.values():
                r.Reset()
                r.Start(False)
        shared.workspace.assistant.ignoreRequests = False
        shared.workspace.assistant.PushMessage('All actionable block(s) have been started.')
    else:
        if not runningActions:
            shared.workspace.assistant.ignoreRequests = False
            return
        for r in shared.runnableBlocks.values():
            if not r.actionFinished.is_set():
                if r.ID in runningActions:
                    if not runningActions[r.ID][0].is_set():
                        r.Pause(False)
        shared.workspace.assistant.PushMessage('All actionable block(s) have been paused.')

def PauseAllActions():
    for r in shared.runnableBlocks.values():
        TogglePause(r, True)

def ReusmeAllActions():
    for r in shared.runnableBlocks.values():
        TogglePause(r, False)

def DetailedView(active = True):
    if active:
        for entity in shared.entities.values():
            if isinstance(entity, Draggable):
                if len(entity.linksIn) > 0:
                    if not entity.popup.scene():
                        shared.activeEditor.scene.addItem(entity.popup)
                    newPos = entity.proxy.scenePos() + entity.FSocketWidgets.pos() + QPoint(100, -30)
                    entity.popup.setPos(newPos)
                    entity.popup.show()
    else:
        for entity in shared.entities.values():
            if isinstance(entity, Draggable):
                    entity.popup.hide()

def CreateBlock(blockType, name: str, pos: QPoint = None, overrideID = None, *args, **kwargs):
    '''Returns a proxy along with its widget.'''
    proxy = QGraphicsProxyWidget()
    editor.scene.addItem(proxy)
    w = blockType(editor, proxy, name = name, overrideID = overrideID, **kwargs)
    print(f'Added {w.name} with ID: {w.ID}')
    name = w.name
    prefix = 'an' if w.name in ['Orbit Response'] else 'a'
    if pos:
        proxy.setWidget(w)
        proxy.setPos(pos)
        w.SetRect()
        w.settings['position'] = [pos.x(), pos.y()]
    rectCenter = proxy.sceneBoundingRect().center()
    shared.workspace.assistant.PushMessage(f'Created {prefix} {name} at ({rectCenter.x():.0f}, {rectCenter.y():.0f})')
    return proxy, w

def CreatePV(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['PV'], 'PV', pos)

def CreateCorrector(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Corrector'], 'Corrector', pos)
    
def CreateBCM(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['BCM'], 'BCM', pos)

def CreateBPM(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['BPM'], 'BPM', pos)

def CreateOrbitResponse(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Orbit Response'], 'Orbit Response', pos)

def CreateView(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['View'], 'View', pos)

def CreateSave(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Save'], 'Save', pos)

def CreateAdd(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Add'], 'Add', pos)

def CreateMultiply(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Multiply'], 'Multiply', pos)

def CreateNumber(pos: QPoint):
    proxy, widegt = CreateBlock(blockTypes['Number'], 'Number', pos)

def CreateSVD(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['SVD'], 'SVD', pos)

def CreateSingleTaskGP(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Single Task GP'], 'Single Task GP', pos)

def CreateLinearKernel(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Linear Kernel'], 'Linear Kernel', pos)

def CreateAnisotropicKernel(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Anisotropic Kernel'], 'Anisotropic Kernel', pos)

def CreatePeriodicKernel(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Periodic Kernel'], 'Periodic Kernel', pos)

def CreateRBFKernel(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['RBF Kernel'], 'RBF Kernel', pos)

def CreateMaternKernel(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Matern Kernel'], 'Matérn Kernel', pos)

def CreateGreaterThan(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['> (Constraint)'], '> (Constraint)', pos)

def CreateLessThan(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['< (Constraint)'], '< (Constraint)', pos)

def CreateGreaterThanFilter(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['> (Filter)'], '> (Filter)', pos)

def CreateLessThanFilter(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['< (Filter)'], '< (Filter)', pos)

def CreateControl(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Control'], 'Control', pos)

def CreateInvert(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Invert'], 'Invert', pos)

def CreateAbsolute(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Absolute'], 'Absolute', pos)

def ToggleGroup(entity):
    entity.settings['showing'] = not entity.settings['showing']
    if not entity.settings['showing']:
        entity.dropdown.setText('\u25BC')
        for item in entity.groupItems:
            item.hide()
            block = item.widget()
            for link in block.linksIn.values():
                link['link'].hide()
            for ID in block.linksOut:
                if ID == 'free':
                    continue
                shared.entities[ID].linksIn[block.ID]['link'].hide()
        entity.proxy.setWidget(None)
        entity.setFixedSize(325, 150)
        entity.note.show()
        entity.layout().activate()
        entity.proxy.setWidget(entity)

        inPos = entity.GetSocketPos('in')
        outPos = entity.GetSocketPos('out')
        for ID, link in entity.linksIn.items():
            ln = link['link'].line()
            ln.setP2(inPos)
            entity.linksIn[ID]['link'].setLine(ln)
            link['link'].show()
        for ID in entity.linksOut:
            if ID == 'free':
                continue
            ln = shared.entities[ID].linksIn[entity.ID]['link'].line()
            ln.setP1(outPos)
            shared.entities[ID].linksIn[entity.ID]['link'].setLine(ln)
            shared.entities[ID].linksIn[entity.ID]['link'].show()
        entity.inSocket.show()
        entity.outSocket.show()
    else:
        entity.dropdown.setText('\u25BA')
        for item in entity.groupItems:
            item.show()
            block = item.widget()
            for link in block.linksIn.values():
                link['link'].show()
            for ID in block.linksOut:
                if ID == 'free':
                    continue
                shared.entities[ID].linksIn[block.ID]['link'].show()
        for link in entity.linksIn.values():
            link['link'].hide()
        for ID in entity.linksOut:
            if ID == 'free':
                continue
            shared.entities[ID].linksIn[entity.ID]['link'].hide()
        entity.note.hide()
        entity.inSocket.hide()
        entity.outSocket.hide()
        entity.proxy.setWidget(None)
        entity.setFixedSize(*entity.settings['size'])
        entity.layout().activate()
        entity.proxy.setWidget(entity)
    shared.activeEditor.scene.update()

def CreateGroup():
    if len(shared.activeEditor.area.selectedItems) < 2:
        shared.workspace.assistant.PushMessage('At least two blocks needed to form a group.', 'Error')
        return
    else:
        invalidIDs = []
        for block in shared.activeEditor.area.selectedBlocks:
            if block.groupID is not None:
                invalidIDs.append(block.ID)
        if invalidIDs != []:
            shared.workspace.assistant.PushMessage(f'The following blocks already belong to other group(s): {', '.join(shared.entities[ID].name for ID in invalidIDs)}.', 'Error')
            return
    proxy, widget = CreateBlock(blockTypes['Group'], 'Group', numBlocks = len(shared.activeEditor.area.selectedBlocks), IDs = [block.ID for block in shared.activeEditor.area.selectedBlocks])
    widget.dropdown.pressed.connect(lambda w = widget: ToggleGroup(w))

def Delete():
    selectedItems = shared.activeEditor.area.selectedItems
    if not selectedItems:
        return
    for item in selectedItems:
        widget = item.widget()
        shared.activeEditor.scene.removeItem(item)
        for ID in widget.linksIn:
            shared.activeEditor.scene.removeItem(widget.linksIn[ID]['link'])
            shared.entities[ID].RemoveLinkOut(widget.ID)
        for ID in widget.linksOut:
            if ID == 'free':
                continue
            # if isinstance(shared.entities[ID], (Add, Multiply)):
            #     shared.entities[ID].RemoveLinkIn(widget.ID)
            # else:
            shared.entities[ID].RemoveLinkIn(widget.ID)
        shared.entities.pop(widget.ID)
        shared.PVs.pop(widget.ID)
        if widget.type == 'PV':
            shared.PVIDs.remove(widget.ID)
            for ID in shared.kernels:
                if shared.entities[ID].type != 'KernelMenu':
                    shared.entities[ID].RemoveLinkedPV(widget.ID)
        elif isinstance(widget, Kernel):
            shared.kernels.pop(shared.kernels.index(widget.ID))
        shared.selectedPV = None
        if widget in shared.activePVs:
            shared.activePVs.remove(widget)
        message = f'Deleted {widget.name}.'
        # if widget is a Group, remove any block references to it
        if widget.type == 'Group':
            for block in widget.groupBlocks:
                block.groupID = None
        elif widget.groupID is not None:
            shared.entities[widget.groupID].groupItems.remove(item)
            shared.entities[widget.groupID].groupBlocks.remove(widget)
            shared.entities[widget.groupID].settings['numBlocks'] -= 1
        widget.stopCheckThread.set()
        widget.deleteLater()
    if len(selectedItems) > 1:
        message = f'Deleted {len(selectedItems)} blocks.'
    shared.activeEditor.area.selectedItems = []
    shared.activeEditor.area.selectedBlocks = []
    shared.activeEditor.area.multipleBlocksSelected = False
    shared.workspace.assistant.PushMessage(message)
    shared.inspector.mainWindowTitle.setText('')
    shared.window.inspector.Push()
    shared.activeEditor.scene.update()
        
def SaveSettings():
    Save()

def Quit():
    shared.window.close()

def ShowMenu(pos: QPoint):
    shared.activeEditor.menu.Show(pos)

# functions to invoke when calling the above functions, to determine which arguments to pass. They all should have a return value.
def GetMousePos():
    return editor.currentPos - shared.editorMenuOffset

# A dict of commands, with values being dicts of format {shortcut = , func = }
commands = {
    'Undo': dict(shortcut = ['Ctrl+Z'], func = Undo, args = []),
    'Redo': dict(shortcut = ['Ctrl+Shift+Z', 'Ctrl+Y'], func = Redo, args = []),
    'Copy': dict(shortcut = ['Ctrl+C'], func = Copy, args = []),
    'Paste': dict(shortcut = ['Ctrl+V'], func = Paste, args = []),
    'Save': dict(shortcut = ['Ctrl+S'], func = SaveSettings, args = []),
    # 'Area Select': dict(shortcut = ['Shift+LMB'], func = lambda: None, args = []),
    'Group': dict(shortcut = ['Ctrl+G'], func = CreateGroup, args = []),
    # 'Snip': dict(shortcut = ['Ctrl+S'], func = Snip, args = []),
    'PV (Process Variable)': dict(shortcut = ['Shift+P'], func = CreatePV, args = [GetMousePos]),
    'Corrector': dict(shortcut = ['Shift+C'], func = CreateCorrector, args = [GetMousePos]),
    'BCM (Beam Current Monitor)': dict(shortcut = [], func = CreateBCM, args = [GetMousePos]),
    'BPM (Beam Position Monitor)': dict(shortcut = ['Shift+B'], func = CreateBPM, args = [GetMousePos]),
    'Orbit Response': dict(shortcut = ['Shift+O'], func = CreateOrbitResponse, args = [GetMousePos]),
    'View': dict(shortcut = ['Shift+V'], func = CreateView, args = [GetMousePos]),
    'Save (Block)': dict(shortcut = ['Shift+S'], func = CreateSave, args = [GetMousePos]),
    'Add (Composition)': dict(shortcut = ['Shift+A'], func = CreateAdd, args = [GetMousePos]),
    'Multiply (Composition)': dict(shortcut = ['Shift+M'], func = CreateMultiply, args = [GetMousePos]),
    'Number': dict(shortcut = ['Shift+N'], func = CreateNumber, args = [GetMousePos]),
    'SVD (Singular Value Decomposition)': dict(shortcut = [], func = CreateSVD, args = [GetMousePos]),
    'Single Task Gaussian Process': dict(shortcut = ['Shift+G'], func = CreateSingleTaskGP, args = [GetMousePos]),
    'Linear Kernel': dict(shortcut = [], func = CreateLinearKernel, args = [GetMousePos]),
    'Anisotropic Kernel': dict(shortcut = [], func = CreateAnisotropicKernel, args = [GetMousePos]),
    'Periodic Kernel': dict(shortcut = [], func = CreatePeriodicKernel, args = [GetMousePos]),
    'Radial Basis Function (RBF) Kernel': dict(shortcut = [], func = CreateRBFKernel, args = [GetMousePos]),
    'Matérn Kernel': dict(shortcut = [], func = CreateMaternKernel, args = [GetMousePos]),
    'Greater Than (Constraint)': dict(shortcut = [], func = CreateGreaterThan, args = [GetMousePos]),
    'Less Than (Constraint)': dict(shortcut = [], func = CreateLessThan, args = [GetMousePos]),
    'Greater Than (Filter)': dict(shortcut = [], func = CreateGreaterThanFilter, args = [GetMousePos]),
    'Less Than (Filter)': dict(shortcut = [], func = CreateLessThanFilter, args = [GetMousePos]),
    'Control (Filter)': dict(shortcut = [], func = CreateControl, args = [GetMousePos]),
    'Invert (Filter)': dict(shortcut = [], func = CreateInvert, args = [GetMousePos]),
    'Absolute (Filter)': dict(shortcut = [], func = CreateAbsolute, args = [GetMousePos]),
    'Toggle All Actions': dict(shortcut = ['Space'], func = ToggleAllActions, args = []),
    'Stop All Actions': dict(shortcut = ['Ctrl+Space'], func = StopAllActions, args = []),
    'Delete': dict(shortcut = ['Delete', 'Backspace'], func = Delete, args = []),
    # 'Detailed View': dict(shortcut = ['Alt+X'], func = DetailedView, args = []),
    'Quit': dict(shortcut = ['Ctrl+W'], func = Quit, args = []),
    'Show Menu': dict(shortcut = ['Ctrl+M'], func = ShowMenu, args = [GetMousePos]),
}

previousActions = [] # Ctrl+Z cycles backwards through this list
undoneActions = [] # Ctrl+Shift+Z / Ctrl+Y cycles through this list, from back to front (stack structure)

def ConnectShortcuts():
    global editor
    editor = shared.editors[0]
    # Get function arguments
    def InvokeAction(action):
        if asyncio.iscoroutinefunction(commands[action]['func']):
            asyncio.create_task(commands[action]['func'](*[arg() for arg in commands[action]['args']]))
        else:
            commands[action]['func'](*[arg() for arg in commands[action]['args']])
    # Connect the shortcuts 
    for k in commands.keys():
        for shortcut in commands[k]['shortcut']:
            QShortcut(QKeySequence(shortcut), editor).activated.connect(lambda k = k: InvokeAction(k))