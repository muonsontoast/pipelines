'''Commands performed inside the editor. Tracks undo and redo actions.'''

from PySide6.QtWidgets import QGraphicsProxyWidget
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import QPoint
from ..blocks.pv import PV
from ..blocks.corrector import Corrector
from ..blocks.bpm import BPM
from ..blocks.orbitresponse import OrbitResponse
from ..blocks.view import View
from .. import shared

editor = None

pv = PV
corrector = Corrector
bpm = BPM
orbitResponse = OrbitResponse
view = View

def Undo():
    pass
def Redo():
    pass
def Copy():
    pass
def Paste():
    pass
def BoxSelect(): # make an area selection
    pass
def Snip(): # cut links
    pass
def AddBlock(blockType, name: str, pos: QPoint, size: tuple = ()):
    '''Returns a proxy along with its widget.'''
    proxy = QGraphicsProxyWidget()
    if size == ():
        w = blockType(editor, proxy, name = name)
    else:
        w = blockType(editor, proxy, name = name, size = size)
    proxy.setWidget(w)
    proxy.setPos(pos)
    editor.scene.addItem(proxy)
    w.SetRect()
    pos = shared.PVs[w.ID]['rect'].center()
    prefix = 'an' if w.name in ['Orbit Response'] else 'a'
    shared.workspace.assistant.PushMessage(f'Created {prefix} {w.name} at ({pos.x():.0f}, {pos.y():.0f})')
    return proxy, w

def AddPV(pos: QPoint):
    proxy, widget = AddBlock(pv, 'PV', pos)

def AddCorrector(pos: QPoint):
    proxy, widget = AddBlock(corrector, 'Corrector', pos)
    
def AddBPM(pos: QPoint):
    proxy, widget = AddBlock(bpm, 'BPM', pos)

def AddOrbitResponse(pos: QPoint):
    proxy, widget = AddBlock(orbitResponse, 'Orbit Response', pos)

def AddView(pos: QPoint):
    proxy, widget = AddBlock(view, 'View', pos)

def Delete():
    if not shared.selectedPV:
        return
    print('Deleting draggable block.')
    editor.scene.removeItem(shared.selectedPV.proxy)
    for ID in shared.selectedPV.linksIn.keys():
        shared.activeEditor.scene.removeItem(shared.selectedPV.linksIn[ID]['link'])
        shared.entities[ID].RemoveLinkOut(shared.selectedPV.ID)
    for ID in shared.selectedPV.linksOut.keys():
        if ID == 'free':
            continue
        shared.entities[ID].RemoveLinkIn(shared.selectedPV.ID)
    shared.PVs.pop(shared.selectedPV.ID)
    shared.workspace.assistant.PushMessage(f'Deleted {shared.selectedPV.name} and removed its connections (if any).')
    shared.selectedPV.deleteLater()
    shared.selectedPV = None
    shared.inspector.mainWindowTitle.setText('')
    shared.window.inspector.Push()
    editor.scene.update()

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
    'Box Select': dict(shortcut = ['Shift+B'], func = BoxSelect, args = []),
    'Snip': dict(shortcut = ['Shift+C'], func = Snip, args = []),
    'Add PV': dict(shortcut = ['Ctrl+Shift+P'], func = AddPV, args = [GetMousePos]),
    'Add Corrector': dict(shortcut = ['Ctrl+Shift+C'], func = AddCorrector, args = [GetMousePos]),
    'Add BPM': dict(shortcut = ['Ctrl+Shift+B'], func = AddBPM, args = [GetMousePos]),
    'Add Orbit Response': dict(shortcut = ['Ctrl+Shift+O'], func = AddOrbitResponse, args = [GetMousePos]),
    'Add View': dict(shortcut = ['Ctrl+Shift+V'], func = AddView, args = [GetMousePos]),
    'Delete': dict(shortcut = ['Delete', 'Backspace'], func = Delete, args = []),
    'Quit': dict(shortcut = ['Ctrl+W'], func = Quit, args = []),
    'Show Menu': dict(shortcut = ['Ctrl+M'], func = ShowMenu, args = [GetMousePos]),
}

previousActions = [] # Ctrl+Z cycles backwards through this list
undoneActions = [] # Ctrl+Shift+Z / Ctrl+Y cycles through this list, from back to front (stack structure)

def ConnectShortcuts():
    global editor
    print('Connecting shortcuts')
    editor = shared.editors[0]
    # Get function arguments
    def InvokeAction(action):
        commands[action]['func'](*[arg() for arg in commands[action]['args']])
    # Connect the shortcuts 
    for k in commands.keys():
        for shortcut in commands[k]['shortcut']:
            QShortcut(QKeySequence(shortcut), editor).activated.connect(lambda k = k: InvokeAction(k))