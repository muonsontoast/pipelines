'''There is a known QPainter error that is raised when maximising the main window in PySide 6.9.1. This is not 
a critical issue and will be resolved in version 6.9.2 around August, so update when you have a chance.'''
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QProgressBar, QStackedLayout, QStyleFactory,
)
from PySide6.QtGui import (
    QIcon, QShortcut, QKeySequence
)
from PySide6.QtCore import Qt
import matplotlib.pyplot as plt
import signal
import sys
import os
from pathlib import Path
from .settings import Settings
from .inspector import Inspector
from .workspace import Workspace
from .latticecanvas import LatticeCanvas
from .font import SetFontToBold
from . import entity
from . import style
from . import shared
from . import linkedcomponent # remove this after testing

plt.rcParams['font.size'] = 10 # Define the font size for plots.

cwd = str(Path.cwd().resolve()) # Get the current working directory.
signal.signal(signal.SIGINT, signal.SIG_DFL) # Allow Ctrl+C interrut from terminal.

class MainWindow(QMainWindow):    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'{shared.windowTitle} - Version {shared.appVersion}')
        self.setWindowIcon(QIcon(f'{cwd}\\app\\PVBuddy.png'))
        shared.latticePath = os.path.abspath(os.path.join(os.getcwd(), '..', 'Lattice', 'dls_ltb.mat')) # for now ...
        self.lightModeOn = False
        entity.mainWindow = self
        # Allow crtl+W shortcut for exit
        QShortcut(QKeySequence('Ctrl+W'), self).activated.connect(self.close)
        # Create an entity for the main window.
        entity.AddEntity(entity.Entity('Page', 'GUI', entity.AssignEntityID(), widget = MainWindow, maximise = True, theme = 'Dark'))
        # Create a master widget to contain everything.
        self.master = QWidget()
        self.master.setLayout(QStackedLayout())
        self.master.setStyleSheet(f'background-color: {style.backgroundColor}; color: {style.fontColor}')
        self.page = QWidget(self.master)
        self.page.setLayout(QGridLayout())
        self.page.layout().setContentsMargins(0, 0, 0, 0)
        self.page.layout().setSpacing(15)
        self.page.layout().setRowMinimumHeight(0, 1)
        self.page.layout().setRowMinimumHeight(1, 165)
        self.page.layout().setRowMinimumHeight(2, 250)
        self.page.layout().setRowMinimumHeight(3, 100)
        self.page.layout().setRowStretch(0, .01)
        self.page.layout().setRowStretch(1, .1)
        self.page.layout().setRowStretch(2, 3)
        self.page.layout().setRowStretch(3, 1.65)
        self.page.setFocusPolicy(Qt.StrongFocus)
        # Add page to the stacked layout.
        self.master.layout().addWidget(self.page)
        # Assign page as the current open window.
        self.master.layout().setCurrentWidget(self.page)
        # Set the central widget.
        self.setCentralWidget(self.master)
        self.master.setContentsMargins(0, 0, 0, 0)
        # Lattice-related vars
        self.filters = {
            'Dipole': True,
            'Quadrupole': True,
            'Sextupole': True,
            'Octupole': True,
            'Corrector': False,
            'RF': False,
            'BPM': False,
            'Screen': False,
            'Collimator': False,
        }
        # Display twiss parameters in the lattice canvas?
        self.showTwiss = False
        shared.lightModeOn = False
        # Does a save file already exist?
        if len(shared.entities) == 1: # no
            # Instantiate the main app components - lattice, editor, inspector, controls, objectives, settings
            self.workspace = Workspace(self)
            self.workspace.setLayout(QStackedLayout())
            entity.AddEntity(entity.Entity('workspace', 'GUI', entity.AssignEntityID(), widget = Workspace))
            self.inspector = Inspector(self)
            self.inspector.AssignSettings(size = (350, None))
            entity.AddEntity(entity.Entity('inspector', 'GUI', entity.AssignEntityID(), widget = Inspector))
            self.latticeCanvas = LatticeCanvas(self)
            entity.AddEntity(entity.Entity('latticeCanvas', 'GUI', entity.AssignEntityID(), widget = LatticeCanvas))
            self.settings = Settings(self)
            entity.AddEntity(entity.Entity('settings', 'GUI', entity.AssignEntityID(), widget = Settings))
        else: # yes
            for e in entity.entities.values():
                if e.type == 'GUI':
                    if e.name in ['latticeCanvas', 'editor', 'inspector', 'controlPVs', 'objectivePVs']: # Check against a whitelist
                        setattr(self, e.name, e.widget()) # Instantiate and make entities directly accessible from the main window.
        shared.lightModeOn = True
        self.page.setStyleSheet(style.Dark01())
        self.page.layout().addWidget(self.latticeCanvas, 1, 1, 1, 8)
        self.page.layout().addWidget(self.workspace, 2, 1, 2, 6)
        self.page.layout().addWidget(self.inspector, 2, 7, 1, 2)
        self.page.layout().addWidget(QWidget(), 3, 7, 1, 2)
        screenPad = 0
        # Small amount of padding at the left of the screen.
        leftPad = QWidget()
        leftPad.setFixedWidth(screenPad)
        self.page.layout().addWidget(leftPad, 1, 0, 3, 1)
        # Small amount of padding at the top of the screen.
        topPad = QWidget()
        topPad.setFixedHeight(screenPad + 5)
        self.page.layout().addWidget(topPad, 0, 0, 1, 10)
        # Small amount of padding at the right of the screen.
        rightPad = QWidget()
        rightPad.setFixedWidth(screenPad)
        self.page.layout().addWidget(rightPad, 1, 9, 3, 1)
        # Small amount of padding at the bottom of the screen.
        bottomPad = QWidget()
        bottomPad.setFixedHeight(screenPad + 5)
        self.page.layout().addWidget(bottomPad, 5, 0, 1, 10)
        # Status text
        self.statusText = QLabel('Status: Idle')
        self.page.layout().addWidget(self.statusText, 4, 1)
        # Progress bar
        self.progressBar = QProgressBar()
        self.progressBar.setAlignment(Qt.AlignCenter)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        SetFontToBold(self.progressBar)
        self.page.layout().addWidget(self.progressBar, 4, 2, 1, 6)
        self.buttonHousing = QWidget()
        self.buttonHousing.setLayout(QHBoxLayout())
        self.buttonHousing.setContentsMargins(0, 0, 10, 0)
        # Settings button
        self.settingsButton = QPushButton('Settings')
        self.settingsButton.pressed.connect(lambda state = 'pressed': style.AdjustButtonColor(self.settingsButton, state))
        self.settingsButton.released.connect(lambda state = 'released': style.AdjustButtonColor(self.settingsButton, state))
        self.settingsButton.setFixedSize(75, 30)
        self.toggleDarkModeButton = QPushButton()
        self.toggleDarkModeButton.clicked.connect(self.ToggleDisplayMode)
        self.toggleDarkModeButton.setText('\u26AA Light Mode')
        self.toggleDarkModeButton.setFixedSize(115, 30)
        self.buttonHousing.layout().addWidget(self.toggleDarkModeButton)
        self.buttonHousing.layout().addWidget(self.settingsButton, alignment = Qt.AlignRight)
        self.page.layout().addWidget(self.buttonHousing, 4, 8)

        # testing linked lattice element here
        l = linkedcomponent.Link(None, None)

        self.showMaximized() # This throws a known but harmless error in PySide 6.9.1, to be corrected in the next version.
    
    def ToggleDisplayMode(self):
        if shared.lightModeOn:
            self.page.setStyleSheet(style.Dark01())
            self.toggleDarkModeButton.setText('\u26AA Light Mode')
        else:
            self.page.setStyleSheet(style.Light01())
            self.toggleDarkModeButton.setText('\u26AB Dark Mode')
        shared.app.processEvents()

    def closeEvent(self, event):
        event.accept()

def GetMainWindow():
    return shared.window

if __name__ == "__main__":
    shared.app = QApplication(sys.argv)
    shared.app.setStyle(QStyleFactory.create('Fusion'))
    window = MainWindow()
    window.show()
    sys.exit(shared.app.exec())
    w = Workspace(None)
    w.show()
    sys.exit(shared.app.exec())