from PySide6.QtWidgets import (
    QWidget, QTabWidget, QListWidget, QListWidgetItem, QLabel, QSlider, QSpacerItem,
    QHBoxLayout, QVBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .expandable import Expandable
from . import shared
from . import style

class Inspector(QTabWidget):
    '''Inspector widget that holds contextual information on currently selected items in the app.'''
    def __init__(self, window):
        super().__init__()
        shared.inspector = self
        self.parent = window
        self.setContentsMargins(0, 0, 0, 0)
        self.settings = dict()
        self.SetSizePolicy()
        self.mainWindow = QWidget()
        self.mainWindow.setLayout(QVBoxLayout())
        self.mainWindow.setContentsMargins(0, 0, 0, 0)
        self.mainWindowTitle = QLabel('')
        self.mainWindowTitle.setFixedHeight(25)
        self.mainWindowTitle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.main = QListWidget()
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
            component = pv.settings['components'][0]['name']
        # Add a row for PV generic information.
        pvName = pv.settings['name']
        name = f'Control PV {pvName[9:]}' if pvName[:9] == 'controlPV' else pvName
        self.mainWindowTitle.setText(name)

        numComponents = len(pv.settings['components'])
        items = [None] * numComponents
        expandables = [None] * numComponents
        for _, c in enumerate(pv.settings['components']):
            name = c['name'] + f' ({c['units']})' if c['units'] != '' else c['name']
            items[_] = QListWidgetItem()
            expandables[_] = Expandable(self.main, items[_], name, pv, _)
            if c['name'] == component:
                expandables[_].ToggleContent()
            items[_].setSizeHint(expandables[_].sizeHint())
            self.main.addItem(items[_])
            self.main.setItemWidget(items[_], expandables[_])
        shared.expandables = expandables
        if not deselecting:
            self.main.setUpdatesEnabled(True)