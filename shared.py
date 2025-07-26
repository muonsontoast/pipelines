from .blocks import pv, orbitresponse, kicker, bpm

'''Globally relevant variables that are shared between all package scripts.'''
entities = [] # States that can be saved between sessions.
appVersion = '0.0.1' # App version.
windowTitle = 'PV Buddy' # App title.
app = None # A reference to the running app.
window = None # Reference to the main window instance.
lightModeOn = True
inspector = None # Displaying additional information about objects.
workspace = None # Workspace containing editors, monitors, etc.
editors = [] # Multiple editor tabs.
proxyPVs = [[]] # Proxy widgets holding the PV widgets.
PVLinkSource = None # A reference to the PV a link is being drawn from (if any).
editorOpenIdx = -1;
controlPVs = None
objectivePVs = None
entities = dict() # store each entity along with its ID for sorting and ID assignment reasons.
entityTypes = ['PV', 'GUI'] # can be more than just PVs, anything you might want to save the state of.
cursorTolerance = 1 # tolerance with which to ignore cursor moves due to hand shake.
PVs = []
activePVs = [] # subset of PVs active -- will only ever be empty or length one, as active ones get cleared up upon clicking other PVs.
expandables = dict() # expandable widgets displayed in the inspector.
selectedPV = None # PV being displayed in the inspector currently.
editorPopup = None # floating popup inside the editor.
latticePath = ''
lattice = None # reference to the lattice
elements = None # lattice element references
names = None # lattice element names
runningCircleFolder = 'C:/Users/shaun/OneDrive/Documents/Optimisation/BO/app/gfx/'
UIMoveUpdateRate = 1000 # number of times to handle UI movement inside the editor per second.
mousePosUponRelease = None # used to determine if the user released the mouse inside another socket.
 
# A dict of block types
blockTypes = {
    'PV': pv.PV,
    'Kicker': kicker.Kicker,
    'BPM': bpm.BPM,
    'Orbit Response': orbitresponse.OrbitResponse,
}
# Need to check whether the cursor is inside a socket. The best way is to keep a record here of all the sockets and their bounding rects.
socketRects = dict()