'''Commands performed inside the editor. Tracks undo and redo actions.'''

from PySide6.QtWidgets import QGraphicsProxyWidget
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import QPoint
from ..blocks.draggable import Draggable
from ..blocks.pv import PV
from ..blocks.corrector import Corrector
from ..blocks.bcm import BCM
from ..blocks.bpm import BPM
from ..blocks.orbitresponse import OrbitResponse
from ..blocks.view import View
from ..blocks.save import Save as SaveBlock
from ..blocks.composition.add import Add
from ..blocks.composition.subtract import Subtract
from ..blocks.composition.svd import SVD
from ..blocks.bayesian.singletaskgp import SingleTaskGP
# kernels
from ..blocks.kernels.linear import LinearKernel
from ..blocks.kernels.anisotropic import AnisotropicKernel
from ..blocks.kernels.periodic import PeriodicKernel
from ..blocks.kernels.rbf import RBFKernel
from ..ui.group import Group
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
    'Subtract': Subtract,
    'SVD': SVD,
    'Single Task GP': SingleTaskGP,
    'Group': Group,
    'Linear Kernel': LinearKernel,
    'Anisotropic Kernel': AnisotropicKernel,
    'Periodic Kernel': PeriodicKernel,
    'RBF Kernel': RBFKernel,
}

def Undo():
    pass
def Redo():
    pass
def Copy():
    pass
def Paste():
    pass
def Snip(): # cut links
    pass

def StopAllActions():
    StopActions()

_toggleState = False

def ToggleAllActions():
    # check which blocks can run and have well-defined inputs.
    global _toggleState
    if not runningActions:
        _toggleState = False
    _toggleState = not _toggleState

    stateText = 'running' if _toggleState else 'paused'
    if _toggleState:
        for r in shared.runnableBlocks.values():
            r.Start()
    else:
        for r in shared.runnableBlocks.values():
            TogglePause(r)
    shared.workspace.assistant.PushMessage(f'All valid actions are {stateText}.')

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
    if blockType != blockTypes['Group']:
        proxy = QGraphicsProxyWidget()
        editor.scene.addItem(proxy)
        w = blockType(editor, proxy, name = name, overrideID = overrideID, **kwargs)
        print(f'Added {w.name} with ID: {w.ID}')
        name = w.name
        prefix = 'an' if w.name in ['Orbit Response'] else 'a'
    else:
        proxy = blockType(*args, **kwargs)
        print(f'Added {proxy.name} with ID: {proxy.ID}')
        prefix = 'a'
        name = proxy.name
    if pos:
        proxy.setWidget(w)
        proxy.setPos(pos)
        w.SetRect()
        w.settings['position'] = [pos.x(), pos.y()]
    rectCenter = proxy.sceneBoundingRect().center()
    shared.workspace.assistant.PushMessage(f'Created {prefix} {name} at ({rectCenter.x():.0f}, {rectCenter.y():.0f})')
    if pos:
        return proxy, w
    return proxy

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

def CreateSubtract(pos: QPoint):
    proxy, widget = CreateBlock(blockTypes['Subtract'], 'Subtract', pos)

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

def CreateGroup():
    if len(shared.activeEditor.area.selectedItems) < 2:
        return print('Too few elements to create a group!')
    proxy = CreateBlock(blockTypes['Group'], 'Group', None, None, *shared.activeEditor.area.selectedItems)

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
            shared.entities[ID].RemoveLinkIn(widget.ID)
        shared.entities.pop(widget.ID)
        shared.PVs.pop(widget.ID)
        shared.selectedPV = None
        if widget in shared.activePVs:
            shared.activePVs.remove(widget)
        message = f'Deleted {widget.name}.'
        widget.deleteLater()
    if len(selectedItems) > 1:
        message = f'Deleted {len(selectedItems)} items.'
    shared.activeEditor.area.selectedItems = []
    print(f'There are now {len(shared.activeEditor.area.selectedItems)} selected items')
    shared.workspace.assistant.PushMessage(message)
    shared.inspector.mainWindowTitle.setText('')
    shared.window.inspector.Push()
    shared.activeEditor.scene.update()
        
def SaveSettings():
    Save()

def Quit():
    if autosave:
        Save()
        shared.window.quitShortcutPressed = True
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
    'Subtract (Composition)': dict(shortcut = [], func = CreateSubtract, args = [GetMousePos]),
    'SVD (Singular Value Decomposition)': dict(shortcut = [], func = CreateSVD, args = [GetMousePos]),
    'Single Task Gaussian Process': dict(shortcut = ['Shift+G'], func = CreateSingleTaskGP, args = [GetMousePos]),
    'Linear Kernel': dict(shortcut = [], func = CreateLinearKernel, args = [GetMousePos]),
    'Anisotropic Kernel': dict(shortcut = [], func = CreateAnisotropicKernel, args = [GetMousePos]),
    'Periodic Kernel': dict(shortcut = [], func = CreatePeriodicKernel, args = [GetMousePos]),
    'RBF Kernel': dict(shortcut = [], func = CreateRBFKernel, args = [GetMousePos]),
    'Toggle All Actions': dict(shortcut = ['Space'], func = ToggleAllActions, args = []),
    'Stop All Actions': dict(shortcut = ['Ctrl+Space'], func = StopAllActions, args = []),
    'Delete': dict(shortcut = ['Delete', 'Backspace'], func = Delete, args = []),
    'Detailed View': dict(shortcut = ['Alt+X'], func = DetailedView, args = []),
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
        commands[action]['func'](*[arg() for arg in commands[action]['args']])
    # Connect the shortcuts 
    for k in commands.keys():
        for shortcut in commands[k]['shortcut']:
            QShortcut(QKeySequence(shortcut), editor).activated.connect(lambda k = k: InvokeAction(k))