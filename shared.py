'''Globally relevant variables that are shared between all package scripts.'''
entities = []
appVersion = '0.0.1' # App version.
windowTitle = 'PV Buddy' # App title.
app = None
window = None # Reference to the main window instance.
lightModeOn = False
inspector = None
workspace = None
editor = None
controlPVs = None
objectivePVs = None
entities = dict() # store each entity along with its ID for sorting and ID assignment reasons.
entityTypes = ['PV', 'GUI'] # can be more than just PVs, anything you might want to save the state of.