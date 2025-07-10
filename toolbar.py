from PySide6.QtWidgets import QWidget, QToolBar, QLabel, QToolButton, QMenu, QCheckBox, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
from .dropdown import FilterButton

class Toolbar(QToolBar):
    '''A toolbar for the main window.'''
    def __init__(self, window):
        super().__init__(window)
        self.parent = window
        self.setIconSize(QSize(24, 24))
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setMovable(False)
        self.setFloatable(False)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        # Lattice-related vars
        self.filters = {
            'Dipoles': True,
            'Quadrupoles': True,
            'Sextupoles': True,
            'Octupoles': True,
            'Correctors': True,
            'RF': False,
            'BPMs': False,
            'Screens': False,
        }
        # Loaded lattice dropdown
        self.loadedLatticeTitle = QLabel('<b style = "font-size:12px;">Loaded Lattice:</b> ')
        self.loadedLatticeWidget = QWidget()
        self.loadedLatticeWidget.setLayout(QHBoxLayout())
        self.loadedLatticeWidget.layout().addWidget(self.loadedLatticeTitle)
        self.loadedLatticeWidget.layout().addWidget(window.loadedLatticeFile)
        self.addWidget(self.loadedLatticeWidget)
        # Lattice filter button
        filterButton = QToolButton()
        filterButton.clicked.connect(filterButton.showMenu)
        filterButton.setText("Filters")
        filterButton.setPopupMode(QToolButton.MenuButtonPopup)
        menu = QMenu()
        filterButton.setEnabled(True)
        menu.setEnabled(True)

        for name, state in self.filters.items():
            item = QCheckBox()
            # action.setCheckable(True)
            # item.setChecked(state)
            # item.toggled.connect(lambda checked, n=name: print(f"{n}: {checked}"))
            menu.addAction(name, lambda: print('Added', name))
        filterButton.setMenu(menu)

        self.addWidget(filterButton)
        # horizontal spacer at the end
        self.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))