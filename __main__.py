'''There is a known QPainter error that is raised when maximising the main window in PySide 6.9.1. This is not 
a critical issue and will be resolved in version 6.9.2 around August, so update when you have a chance.'''
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QFrame, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QProgressBar, QStackedLayout, QStyleFactory,
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt
import qasync
import asyncio
import matplotlib.pyplot as plt
import signal
import sys
import os
import time
from pathlib import Path
from .utils import cothread
from .inspector import Inspector
from .ui.workspace import Workspace
from .lattice.latticeglobal import LatticeGlobal
from .lattice import latticeutils
from .font import SetFontToBold
from .utils.entity import Entity
from .utils import memory
from .utils.commands import ConnectShortcuts, Save, StopAllActions
from .utils.load import Load
from . import style
from . import shared

plt.rcParams['font.size'] = 10 # Define the font size for plots.
cwd = str(Path.cwd().resolve()) # Get the current working directory.
signal.signal(signal.SIGINT, signal.SIG_DFL) # Allow Ctrl+C interrupt from terminal.

class MainWindow(Entity, QMainWindow):
    def __init__(self, latticeName = ''):
        super().__init__(name = 'MainWindow', type = 'MainWindow')
        settingsPath = os.path.join(shared.cwd, 'config', 'settings.yaml')
        shared.window = self
        self.setWindowTitle(f'{shared.windowTitle} - Early Prototype')
        self.setWindowIcon(QIcon(f'{cwd}\\pipelines\\\\gfx\\icon.png'))
        self.quitShortcutPressed = False
        # Create a compressed folder for commonly referenced frames if it doesn't already exist (first time setup).
        compressedFolderPath = os.path.join(shared.cwd, 'gfx\\compressed')
        if not os.path.exists(compressedFolderPath):
            print('There are no existing compressed frames. Compressing and storing them inside the \\gfx\\ folder (first time setup).')
            os.makedirs(compressedFolderPath)
            os.makedirs(os.path.join(compressedFolderPath, 'running\\grey'))
            os.makedirs(os.path.join(compressedFolderPath, 'running\\black'))
            t = time.time()
            fullResFrames = [None for _ in range(shared.runningCircleNumFrames)]
            for _ in range(shared.runningCircleNumFrames):
                specificPathG = f'running\\grey\\{_}.png'
                specificPathB = f'running\\black\\{_}.png'
                path = os.path.join(shared.cwd, 'gfx', specificPathG)
                frame = QPixmap(path)
                fullResFrames[_] = frame
                scaledFrame = frame.scaled(
                    shared.runningCircleResolution, shared.runningCircleResolution,
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation
                )
                scaledFrame.setDevicePixelRatio(1.0)
                scaledFrame.save(os.path.join(compressedFolderPath, specificPathG))
                shared.runningCircleFrames[_] = scaledFrame
                path = os.path.join(shared.cwd, 'gfx', specificPathB)
                scaledFrame = QPixmap(path).scaled(
                    shared.runningCircleResolution, shared.runningCircleResolution,
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation
                )
                scaledFrame.setDevicePixelRatio(1.0)
                scaledFrame.save(os.path.join(compressedFolderPath, specificPathB))
            print(f'Finished compressing and loading frames ({memory.GetFrameArraySize(fullResFrames):.2f} MB compressed to {memory.GetFrameArraySize(shared.runningCircleFrames) * 2:.2f} MB in {time.time() - t:.3f} seconds)')
        else:
            print('Loading compressed frames ...')
            defaultRunningCirclePath = os.path.join(compressedFolderPath, 'running\\grey')
            t = time.time()
            for _ in range(shared.runningCircleNumFrames):
                shared.runningCircleFrames[_] = QPixmap(os.path.join(defaultRunningCirclePath, f'{_}.png'))
            print(f'Finished loading compressed frames in {time.time() - t:.3f} seconds.')
        # Create a folder for saving data held in blocks (not sessions)
        dataDumpPath = os.path.join(shared.cwd, 'datadump')
        if not os.path.exists(dataDumpPath):
            print('Data dump folder does not exist, creating one.')
            os.mkdir(dataDumpPath)
        # Load lattice
        shared.latticePath = os.path.join(shared.cwd, 'lattice-saves')
        # create a lattice-saves folder if one doesn't already exist.
        if not os.path.exists(shared.latticePath):
            print(f'Lattice save folder \'lattice-saves\' does not exist, creating one. Any custom lattice files should be stored here.')
            os.mkdir(shared.latticePath)
            # Path(os.path.join(shared.latticePath, '.gitignore')).touch()
            (Path(shared.latticePath) / '.gitignore').write_text('# Store any custom .mat lattice files in this folder.')
        if shared.elements is None:
            formattedLatticePath = Path(shared.latticePath)
            fullPathName = ''
            files = sorted(list(formattedLatticePath.glob('*.mat')))
            if files:
                print('Found saved lattice(s):', files)
                if latticeName == '':
                    print(f'A lattice name was not specified as an additional argument in the CLI. Loading the first alphabetical lattice \'{files[0]}\'.')
                    shared.lattice = latticeutils.LoadLattice(files[0])
                    fullPathName = files[0]
                else:
                    latticeName = latticeName.split('.')[0] + '.mat' # ensure correct file extension
                    try:
                        print(f'Attempting to load saved lattice \'{latticeName}\'.')
                        fullPathName = os.path.join(formattedLatticePath, latticeName)
                        shared.lattice = latticeutils.LoadLattice(fullPathName)
                    except:
                        print(f'No saved lattices were found with the name \'{latticeName}\'. Defaulting to first alphabetical lattice \'{files[0]}\'.')
                        shared.lattice = latticeutils.LoadLattice(files[0])
                        fullPathName = files[0]
                shared.latticePath = fullPathName
                shared.elements = latticeutils.GetLatticeInfo(shared.lattice)
                shared.names = [a + f' [{shared.elements.Type[b]}] ({str(b)})' for a, b in zip(shared.elements.Name, shared.elements.Index)]
            else:
                print('No saved lattices found.')
        self.lightModeOn = False
        shared.mainWindow = self
        # Create a master widget to contain everything.
        self.master = QWidget()
        self.master.setLayout(QStackedLayout())
        self.master.setStyleSheet(f'background-color: {style.backgroundColor}; color: {style.fontColor}')
        self.page = QWidget(self.master)
        self.page.setLayout(QGridLayout())
        self.page.layout().setContentsMargins(0, 0, 0, 0)
        self.page.layout().setSpacing(15)
        self.page.layout().setRowMinimumHeight(0, 1)
        self.page.layout().setRowMinimumHeight(1, 100)
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
            self.latticeGlobal = LatticeGlobal(self)
            self.inspector = Inspector(self)
        shared.lightModeOn = True
        # connect key shortcuts to their functions.
        ConnectShortcuts()
        self.page.setStyleSheet(style.Dark01())
        self.page.layout().addWidget(QFrame(), 1, 7, 1, 2)
        self.page.layout().addWidget(self.latticeGlobal, 1, 1, 1, 6)
        self.page.layout().addWidget(self.workspace, 2, 1, 2, 6)
        self.page.layout().addWidget(self.inspector, 2, 7, 2, 2)
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
        # Give the editor focus by default
        shared.activeEditor.setFocus()
        # shared.app.processEvents()

        # Load in settings if they exist and apply to existing entities, and create new ones if they don't already exist.
        print('Loading settings from:', settingsPath)
        Load(settingsPath)
        
        self.showMaximized() # This throws a known but harmless error in PySide 6.9.1, to be corrected in the next version.
    
    async def ConfigureLoop(self):
        # Setup an event loop to handle asynchronous PV I/O without blocking the UI thread.
        loop = asyncio.get_running_loop()
        self.future = loop.create_future() # store a reference that can be cancelled later.
        try:
            await self.future
        except asyncio.CancelledError: # gracefully close the event loop when the app is exited.
            pass
    
    def ToggleDisplayMode(self):
        if shared.lightModeOn:
            self.page.setStyleSheet(style.Dark01())
            self.toggleDarkModeButton.setText('\u26AA Light Mode')
        else:
            self.page.setStyleSheet(style.Light01())
            self.toggleDarkModeButton.setText('\u26AB Dark Mode')
        shared.app.processEvents()

    def closeEvent(self, event):
        StopAllActions()
        if not self.quitShortcutPressed:
            Save()
        if hasattr(self, 'future') and self.future and not self.future.done():
            self.future.cancel()
        event.accept()

def GetMainWindow():
    return shared.window

if __name__ == "__main__":
    shared.app = QApplication(sys.argv)
    shared.app.setStyle(QStyleFactory.create('Fusion'))
    # skip first arg which is app name.
    window = MainWindow(*sys.argv[1:])
    window.show()
    # sys.exit(shared.app.exec())
    qasync.run(window.ConfigureLoop())