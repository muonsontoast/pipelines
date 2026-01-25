import os
from pathlib import Path
from PySide6.QtCore import QPoint

'''Globally relevant variables that are shared between all package scripts.'''
cwd = os.path.join(str(Path.cwd().resolve()), 'pipelines') # Get the current working directory.
appVersion = '0.0.1' # App version.
windowTitle = 'Pipelines' # App title.
app = None # A reference to the running app.
window = None # Reference to the main window instance.
lightModeOn = True
inspector = None # Displaying additional information about objects.
workspace = None # Workspace containing editors, monitors, etc.
editors = [] # Multiple editor tabs.
activeEditor = None
proxyPVs = [[]] # Proxy widgets holding the PV widgets.
PVLinkSource = None # A reference to the PV a link is being drawn from (if any).
editorOpenIdx = -1;
controlPVs = None # will be deprecated
objectivePVs = None # will be deprecated
entities = dict() # store each entity along with its ID for sorting and ID assignment reasons.
PVIDs = [] # easy lookup list so entity iterations aren't necessary.
entityTypes = ['PV', 'GUI'] # can be more than just PVs, anything you might want to save the state of.
cursorTolerance = 2.5 # tolerance with which to ignore cursor moves due to hand shake.
# PVs = []
PVs = dict()
activePVs = [] # subset of PVs active -- will only ever be empty or length one, as active ones get cleared up upon clicking other PVs.
expandables = dict() # expandable widgets displayed in the inspector.
runnableBlocks = dict() # removes the number of blocks that have to be iterated over when toggling actions.
# runningBlocks = dict() # blocks currently performing actions.
selectedPV = None # PV being displayed in the inspector currently. -- to be deprecated
selectedPVs = []
editorPopup = None # floating popup inside the editor.
latticePath = ''
lattice = None # reference to the lattice
elements = None # lattice element references
names = None # lattice element names
runningCircleNumFrames = 119
runningCircleResolution = 30 # z x z pixels
runningCircleFrames = [None for _ in range(runningCircleNumFrames)] # frames used by the circle indicating progress in blocks.
UIMoveUpdateRate = 480 # number of times to handle UI movement inside the editor per second.
currentMousePos = None
mousePosUponRelease = None # used to determine if the user released the mouse inside another socket.
kernelMenu = None # store a reference to the existing open kernel menu if it exists inside the editor.
kernelContext = None # a reference to the button that opened the kernel context view.
lastActionPerformed = None
editorMenuOffset = QPoint(30, 30)
editorSelectMode = False
selected = [] # list of selected entity IDs
kernels = [] # list of kernels
toggleState = False # should blocks be run (True) or paused (False) when Spacebar is pressed?
changeToggleState = True # override the change toggle state logic
stopCleanUpTimer = False