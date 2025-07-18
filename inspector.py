from PySide6.QtWidgets import (
    QWidget, QTabWidget, QListWidget, QListWidgetItem, QLabel,
    QVBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .expandable import Expandable
from . import shared

class Inspector(QTabWidget):
    '''Inspector widget that holds contextual information on currently selected items in the app.'''
    def __init__(self, window):
        super().__init__()
        shared.inspector = self
        self.parent = window
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumWidth(415)
        # self.resize(200, 100)
        self.settings = dict()
        self.SetSizePolicy()
        self.mainWindow = QWidget()
        self.mainWindow.setLayout(QVBoxLayout())
        self.mainWindow.layout().setContentsMargins(0, 15, 0, 0)
        self.mainWindowTitle = QLabel('')
        self.mainWindowTitle.setFixedHeight(25)
        self.mainWindowTitle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main = QListWidget()
        self.main.setFocusPolicy(Qt.NoFocus)
        self.main.setSelectionMode(QListWidget.NoSelection)
        self.main.setFrameShape(QListWidget.NoFrame)
        self.main.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.main.setSpacing(0)
        self.main.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Construct the main window
        self.mainWindow.layout().addWidget(self.mainWindowTitle)
        self.mainWindow.layout().addWidget(self.main)
        # Define the scan tab for detailed information on scanning.
        self.scan = QListWidget()
        # Define the optimiser tab for detailed information on optimisation.
        self.optimiser = QListWidget()
        # Add tabs
        self.addTab(self.mainWindow, 'Inspector')
        self.addTab(self.scan, 'Scan')
        self.addTab(self.optimiser, 'Optimiser')
        self.Push()

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings
    
    def SetSizePolicy(self):
        # Set the size
        size = self.settings.get('size', (None, None))
        sizePolicy = [None, None]
        # Set horizontal
        if size[0] is None:
            sizePolicy[0] = QSizePolicy.Expanding
        else:
            self.setFixedWidth(size[0])
            sizePolicy[0] = QSizePolicy.Preferred
        # Set vertical
        if size[1] is None:
            sizePolicy[1] = QSizePolicy.Expanding
        else:
            self.setFixedHeight(size[1])
            sizePolicy[1] = QSizePolicy.Preferred
        self.setSizePolicy(*sizePolicy)
    
    def Push(self, pv = None, component = None, deselecting = False):
        if not deselecting:
            self.main.setUpdatesEnabled(False) # prevents flashing when redrawing the inspector
        self.main.clear()
        if pv is None:
            return
        if component is None:
            component = pv.settings['components']['value']['name']
        # Add a row for PV generic information.
        pvName = pv.settings['name']
        name = f'Control PV {pvName[9:]}' if pvName[:9] == 'controlPV' else pvName
        self.mainWindowTitle.setText(name)

        items = dict()
        expandables = dict()
        for k, c in pv.settings['components'].items():
            if 'units' in c.keys():
                name = c['name'] + f' ({c['units']})'
            else:
                name = c['name']
            items[k] = QListWidgetItem()
            expandables[k] = Expandable(self.main, items[k], name, pv, k)
            if c['name'] == component:
                expandables[k].ToggleContent()
            items[k].setSizeHint(expandables[k].sizeHint())
            self.main.addItem(items[k])
            self.main.setItemWidget(items[k], expandables[k])
        shared.expandables = expandables
        if not deselecting:
            self.main.setUpdatesEnabled(True)