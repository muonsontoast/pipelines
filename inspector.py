from PySide6.QtWidgets import (
    QWidget, QTabWidget, QListWidget, QListWidgetItem, QSlider, QSpacerItem,
    QHBoxLayout, QVBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .expandable import Expandable
from .clearfocuslist import ClearFocusListWidget

class Inspector(QTabWidget):
    '''Inspector widget that holds contextual information on currently selected items in the app.'''
    def __init__(self, window):
        super().__init__()
        self.parent = window
        self.setContentsMargins(0, 0, 0, 0)
        self.settings = dict()
        self.SetSizePolicy()
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
        # Set size policy
        self.setSizePolicy(*sizePolicy)
    
    def Push(self, pv = None, component = None):
        self.ClearLayout()
        self.main = ClearFocusListWidget()
        self.main.setFrameShape(QListWidget.NoFrame)
        self.main.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.main.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main.setSpacing(0)
        self.main.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Define the scan tab for detailed information on scanning.
        self.scan = QListWidget()
        # Define the optimiser tab for detailed information on optimisation.
        self.optimiser = QListWidget()
        # Add tabs
        self.addTab(self.main, 'Inspector')
        self.addTab(self.scan, 'Scan')
        self.addTab(self.optimiser, 'Optimiser')
        # Has a PV been supplied?
        if pv is None:
            return
        if component is None:
            component = pv.settings['components'][0]['name']
        # Add a row for PV generic information.
        pvName = pv.settings['name']
        name = f'Control PV {pvName[9:]}' if pvName[:9] == 'controlPV' else pvName
        self.main.SetName(name)

        numComponents = len(pv.settings['components'])
        items = [None] * numComponents
        expandables = [None] * numComponents
        for _, c in enumerate(pv.settings['components']):
            items[_] = QListWidgetItem()
            expandables[_] = Expandable(self.main, items[_], c['name'])    
            # Expand the component if it is the one being selected.
            for k, v in c.items():
                if k == 'value':
                    w = QWidget()
                    w.setLayout(QHBoxLayout())
                    w.setContentsMargins(0, 0, 0, 0)
                    slider = QSlider(Qt.Horizontal)
                    slider.setMinimum(0)
                    slider.setMaximum(1000000)
                    slider.setValue(0)
                    w.layout().addWidget(slider)
                    w.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
                    expandables[_].contentWidgets[k] = w
            if c['name'] == component:
                expandables[_].ToggleContent()
            self.main.addItem(items[_])
            self.main.setItemWidget(items[_], expandables[_])

    def ClearLayout(self):
        for i in reversed(range(self.count())):
            self.removeTab(i)
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()