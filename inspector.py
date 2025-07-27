from PySide6.QtWidgets import (
    QWidget, QTabWidget, QListWidget, QListWidgetItem, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .expandable import Expandable
from . import shared
from . import style

class Inspector(QTabWidget):
    '''Inspector widget that holds contextual information on currently selected items in the app.'''
    def __init__(self, window):
        super().__init__()
        print('setting shared.inspector')
        shared.inspector = self
        print('has it been assigned?', shared.inspector is not None)
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
            if 'value' in pv.settings['components'].keys():
                component = pv.settings['components']['value']['name']
            else:
                component = 'Linked Lattice Element'
        # Add a row for PV generic information.
        pvName = pv.settings['name']
        name = f'Control PV {pvName[9:]}' if pvName[:9] == 'controlPV' else pvName
        self.mainWindowTitle.setText(name)

        self.items = dict()
        self.expandables = dict()

        # Add an alignment item at the top if one is needed by the component.
        if pv.__class__ in [shared.blockTypes['Kicker'], shared.blockTypes['BPM']]:
            self.items['alignment'] = QListWidgetItem()
            planeRow = QWidget()
            planeRow.setLayout(QHBoxLayout())
            planeRow.layout().setContentsMargins(2, 0, 10, 0)
            if pv.settings['alignment'] == 'Horizontal':
                text = 'Aligned to <span style = "color: #bc4444">Horizontal</span> plane.'
            else:
                text = 'Aligned to <span style = "color: #399a26">Vertical</span> plane.'
            self.state = QLabel(text)
            self.state.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            planeRow.layout().addWidget(self.state)
            self.toggle = QPushButton('Swap Plane')
            self.toggle.setFixedSize(100, 35)
            self.toggle.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#1e1e1e', fontColor = '#c4c4c4'))
            self.toggle.clicked.connect(lambda: self.SwapPlane(pv))
            planeRow.layout().addWidget(self.toggle)
            self.items['alignment'].setSizeHint(planeRow.sizeHint())
            self.main.addItem(self.items['alignment'])
            self.main.setItemWidget(self.items['alignment'], planeRow)

        for k, c in pv.settings['components'].items():
            if 'units' in c.keys():
                name = c['name'] + f' ({c['units']})'
            else:
                name = c['name']
            self.items[k] = QListWidgetItem()
            self.expandables[k] = Expandable(self.main, self.items[k], name, pv, k)
            if c['name'] == component:
                self.expandables[k].ToggleContent()
            self.items[k].setSizeHint(self.expandables[k].sizeHint())
            self.main.addItem(self.items[k])
            self.main.setItemWidget(self.items[k], self.expandables[k])
        shared.expandables = self.expandables
        if not deselecting:
            self.main.setUpdatesEnabled(True)

    def SwapPlane(self, pv):
        if pv.settings['alignment'] == 'Horizontal':
            pv.settings['alignment'] = 'Vertical'
            self.state.setText('Aligned to <span style = "color: #399a26">Vertical</span> plane.')
        else:
            pv.settings['alignment'] = 'Horizontal'
            self.state.setText('Aligned to <span style = "color: #bc4444">Horizontal</span> plane.')
        print(f'Updating pv colors for {pv.settings['name']}!')
        pv.UpdateColors()
        for e in self.expandables.values():
            e.widget.UpdateColors()