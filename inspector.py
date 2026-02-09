from PySide6.QtWidgets import (
    QApplication, QWidget, QTabWidget, QListWidget, QListWidgetItem, QLineEdit,
    QVBoxLayout, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QSize
from .expandable import Expandable
from .utils.entity import Entity
from . import shared
from . import style

class Inspector(Entity, QTabWidget):
    '''Inspector widget that holds contextual information on currently selected items in the app.'''
    def __init__(self, parent, **kwargs):
        # -1 size corresponds to an expanding size policy.
        size = kwargs.pop('size', [500, -1])
        super().__init__(name = 'Inspector', type = 'Inspector', size = size)
        shared.inspector = self
        self.parent = parent
        self.selectedBlocks = [item.widget() for item in shared.activeEditor.area.selectedItems]
        self.multipleBlocksSelected = len(self.selectedBlocks) > 1
        self.setMaximumWidth(size[0])
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.mainWindow = QWidget()
        self.mainWindow.setLayout(QVBoxLayout())
        self.mainWindow.layout().setContentsMargins(10, 10, 10, 0)
        # Changing mainWindowTitle from label to line edit
        self.mainWindowTitleWidget = QWidget()
        self.mainWindowTitleWidget.setLayout(QHBoxLayout())
        self.mainWindowTitleWidget.layout().setContentsMargins(10, 5, 10, 5)
        self.mainWindowTitle = QLineEdit()
        self.ignoreTextChange = False
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
        self.ToggleStyling()
        self.Push()

    def Push(self, pv = None, component = None):
        self.main.setUpdatesEnabled(False)
        self.main.clear()
        if not pv:
            self.main.hide()
            self.mainWindowTitleWidget.hide()
            return
        self.mainWindowTitle.setReadOnly(False)
        if not component:
            if 'value' in pv.settings['components']:
                component = pv.settings['components']['value']['name']
            elif 'linkedLatticeElement' in pv.settings['components']:
                component = 'Linked Lattice Element'
            elif len(pv.settings['components']) > 0:
                component = next(iter(pv.settings['components'].values()))['name']
        # Add a row for PV generic information.
        pvName = pv.settings['name']
        self.ignoreTextChange = True
        self.mainWindowTitle.setText(pvName)
        self.ignoreTextChange = False

        self.items = dict()
        self.expandables = dict()

        if self.mainWindowTitleWidget.isHidden():
            self.main.setUpdatesEnabled(True)

        for k, c in sorted(pv.settings['components'].items(), key = self.SortName):
            if 'units' in c.keys() and c['units'] != '':
                name = c['name'] + f' ({c['units']})'
            else:
                name = c['name']
            self.items[k] = QListWidgetItem()
            self.expandables[k] = Expandable(self.main, self.items[k], name, pv, k)
            if c['name'] == component or c['name'] == 'Linked Lattice Element' or len(pv.settings['components']) == 1:
                self.expandables[k].ToggleContent()
            self.items[k].setSizeHint(self.expandables[k].sizeHint())
            self.main.addItem(self.items[k])
            self.main.setItemWidget(self.items[k], self.expandables[k])
        shared.expandables = self.expandables
        self.main.setUpdatesEnabled(True)
        if self.mainWindowTitleWidget.isHidden():
            self.mainWindowTitleWidget.show()
            self.main.show()
        self.ToggleStyling()

    def PushMultiple(self):
        '''Displays common components amongst selected blocks.'''
        self.main.setUpdatesEnabled(False)
        self.main.clear()
        self.mainWindowTitle.blockSignals(True)
        self.mainWindowTitle.setText(f'{len(shared.activeEditor.area.selectedItems)} selected items.')
        self.mainWindowTitle.setReadOnly(True)
        self.mainWindowTitle.blockSignals(False)

        self.items = dict()
        self.expandables = dict()

        if self.mainWindowTitleWidget.isHidden():
            self.main.setUpdatesEnabled(True)

        commonComponents = dict()
        selectedBlock = shared.activeEditor.area.selectedItems[0].widget()
        for common in shared.activeEditor.commonComponents:
            c = selectedBlock.settings['components'][common]
            commonComponents[common] = c
        for k, c in sorted(commonComponents.items(), key = self.SortName):
            if 'units' in c.keys() and c['units'] != '':
                name = c['name'] + f' ({c['units']})'
            else:
                name = c['name']
            self.items[k] = QListWidgetItem()
            self.expandables[k] = Expandable(self.main, self.items[k], name, selectedBlock, k)
            self.expandables[k].ToggleContent()
            self.items[k].setSizeHint(self.expandables[k].sizeHint())
            self.main.addItem(self.items[k])
            self.main.setItemWidget(self.items[k], self.expandables[k])
        shared.expandables = self.expandables

        self.main.setUpdatesEnabled(True)
        self.main.show()

    def SortName(self, item):
        key, component = item
        return key == 'linkedLatticeElement'

    def UpdateListWidgetItemWidths(self):
        for k, e in self.expandables.items():
            self.items[k].setSizeHint(e.sizeHint())
            self.main.addItem(self.items[k])
            self.main.setItemWidget(self.items[k], self.expandables[k])
        def AllowUpdates():
            self.main.setUpdatesEnabled(True)
        QTimer.singleShot(0, AllowUpdates)

    def TextChanged(self):
        if shared.selectedPV is None or self.ignoreTextChange:
            return
        shared.selectedPV.name = self.mainWindowTitle.text()
        shared.selectedPV.settings['name'] = shared.selectedPV.name
        shared.selectedPV.title.setText(shared.selectedPV.name)

    def TextSet(self):
        self.TextChanged()
        self.mainWindowTitle.clearFocus()

    def SwapPlane(self, pv):
        if pv.settings['alignment'] == 'Horizontal':
            pv.settings['alignment'] = 'Vertical'
            self.state.setText('Aligned to <span style = "color: #399a26">Vertical</span> plane.')
        else:
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