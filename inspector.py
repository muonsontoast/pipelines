from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QListWidget, QListWidgetItem, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from .expandable import Expandable
from .utils.entity import Entity
from . import shared
from . import style

class Inspector(Entity, QTabWidget):
    '''Inspector widget that holds contextual information on currently selected items in the app.'''
    def __init__(self, parent, **kwargs):
        # -1 size corresponds to an expanding size policy.
        size = kwargs.pop('size', [415, -1])
        super().__init__(name = 'Inspector', type = 'Inspector', size = size)
        shared.inspector = self
        self.parent = parent
        self.setMinimumWidth(size[0])
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mainWindow = QWidget()
        self.mainWindow.setLayout(QVBoxLayout())
        self.mainWindow.layout().setContentsMargins(10, 10, 10, 0)
        # Changing mainWindowTitle from label to line edit
        self.mainWindowTitleWidget = QWidget()
        self.mainWindowTitleWidget.setLayout(QHBoxLayout())
        self.mainWindowTitleWidget.layout().setContentsMargins(10, 5, 10, 5)
        self.mainWindowTitle = QLineEdit()
        self.mainWindowTitle.textChanged.connect(self.TextChanged)
        self.mainWindowTitle.returnPressed.connect(self.TextSet)
        self.mainWindowTitle.setFixedHeight(35)
        self.mainWindowTitle.setObjectName('title')
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
        self.mainWindowTitleWidget.layout().addWidget(self.mainWindowTitle)
        self.mainWindow.layout().addWidget(self.mainWindowTitleWidget)
        self.mainWindow.layout().addWidget(self.main)
        self.addTab(self.mainWindow, 'Inspector')
        self.Push()
        self.ToggleStyling()

    def Push(self, pv = None, component = None):
        self.main.setUpdatesEnabled(False)
        self.main.clear()
        self.toggle = QPushButton('Swap Plane')
        self.toggle.setFixedSize(100, 35)
        if not pv:
            self.mainWindowTitleWidget.hide()
            self.main.hide()
            print('No PV supplied to the inspector.')
            return

        if not component:
            if 'value' in pv.settings['components'].keys():
                component = pv.settings['components']['value']['name']
            else:
                component = 'Linked Lattice Element'
        self.mainWindowTitleWidget.show()
        self.main.show()
        # Add a row for PV generic information.
        pvName = pv.settings['name']
        self.mainWindowTitle.setText(pvName)

        self.items = dict()
        self.expandables = dict()

        # Add an alignment item at the top if one is needed by the component.
        # if pv.type in ['Corrector', 'BPM']:
        if 'alignment' in pv.settings:
            self.items['alignment'] = QListWidgetItem()
            if pv.settings['alignment'] == 'Horizontal':
                text = 'Aligned to <span style = "color: #bc4444">Horizontal</span> plane.'
            else:
                text = 'Aligned to <span style = "color: #399a26">Vertical</span> plane.'
            self.state = QLabel(text)
            self.state.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.planeRow = QWidget()
            self.planeRow.setLayout(QHBoxLayout())
            self.planeRow.layout().setContentsMargins(2, 0, 10, 0)
            self.planeRow.layout().addWidget(self.state)
            self.toggle.clicked.connect(lambda: self.SwapPlane(pv))
            self.planeRow.layout().addWidget(self.toggle)
            self.items['alignment'].setSizeHint(self.planeRow.sizeHint())
            self.main.addItem(self.items['alignment'])
            self.main.setItemWidget(self.items['alignment'], self.planeRow)

        def SortName(item):
            key, component = item
            return key == 'linkedLatticeElement'

        for k, c in sorted(pv.settings['components'].items(), key = SortName):
            if 'units' in c.keys():
                name = c['name'] + f' ({c['units']})'
            else:
                name = c['name']
            self.items[k] = QListWidgetItem()
            self.expandables[k] = Expandable(self.main, self.items[k], name, pv, k)
            if c['name'] == component or c['name'] == 'Linked Lattice Element':
                self.expandables[k].ToggleContent()
            self.items[k].setSizeHint(self.expandables[k].sizeHint())
            self.main.addItem(self.items[k])
            self.main.setItemWidget(self.items[k], self.expandables[k])
        shared.expandables = self.expandables
        self.ToggleStyling()
        self.main.setUpdatesEnabled(True)

    def UpdateListWidgetItemWidths(self):
        for k, e in self.expandables.items():
            self.items[k].setSizeHint(e.sizeHint())
            self.main.addItem(self.items[k])
            self.main.setItemWidget(self.items[k], self.expandables[k])
        def AllowUpdates():
            self.main.setUpdatesEnabled(True)
        QTimer.singleShot(0, AllowUpdates)

    def TextChanged(self):
        if shared.selectedPV is None:
            return
        shared.selectedPV.name = self.mainWindowTitle.text()
        shared.selectedPV.settings['name'] = shared.selectedPV.name
        shared.selectedPV.title.setText(shared.selectedPV.name)

    def TextSet(self):
        self.TextChanged()
        self.mainWindowTitle.clearFocus()

    def SwapPlane(self, pv):
        if pv.settings['alignment'] == 'Horizontal':
            print('Swapping plane to Vertical')
            pv.settings['alignment'] = 'Vertical'
            self.state.setText('Aligned to <span style = "color: #399a26">Vertical</span> plane.')
        else:
            print('Swapping plane to Horizontal')
            pv.settings['alignment'] = 'Horizontal'
            self.state.setText('Aligned to <span style = "color: #bc4444">Horizontal</span> plane.')

    def UpdateColors(self):
        pass

    def ToggleStyling(self):
        '''Accepts an `override` which should be True or False.'''
        if shared.lightModeOn:
            pass
        else:
            self.mainWindow.setStyleSheet(style.WidgetStyle(color = '#1a1a1a', marginLeft = 0, marginRight = 0, borderThickness = 0))
            self.mainWindowTitleWidget.setStyleSheet(style.WidgetStyle(color = '#222222', borderRadius = 2, marginLeft = 0, marginRight = 0, borderThickness = 0))
            self.toggle.setStyleSheet(style.PushButtonStyle(color = '#262626', hoverColor = '#3d3d3d', fontColor = '#c4c4c4', padding = 0))