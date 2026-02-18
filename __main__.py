from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QGridLayout,
    QLabel, QStackedLayout, QStyleFactory,
    QSizePolicy,
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer
import qasync
import asyncio
import matplotlib.pyplot as plt
import at
import signal
import sys
import os
import time
import psutil
from cpuinfo import get_cpu_info
import subprocess
from datetime import datetime
from pathlib import Path
from threading import Thread
import faulthandler
faulthandler.enable()
from .inspector import Inspector
from .ui.workspace import Workspace
from .ui.groupmenu import GroupMenu
from .lattice.latticeglobal import LatticeGlobal
from .lattice import latticeutils
from .utils.entity import Entity
from .utils import memory
from .utils.commands import ConnectShortcuts, Save, StopAllActions
from .utils.resourcemonitor import ResourceMonitor
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
        appPth = Path(__file__).resolve().parent
        appVersion = subprocess.run(
            ['git', 'describe', '--tags', '--always'],
            cwd = appPth,
            capture_output = True,
            text = True,
        )
        commitDateAndTime = subprocess.run(
            ['git', 'show', '-s', '--format=%cd', '--date=iso'],
            cwd = appPth,
            capture_output = True,
            text = True,
        )
        dt = datetime.fromisoformat(commitDateAndTime.stdout.strip())
        self.setWindowTitle(f'{shared.windowTitle} - commit {appVersion.stdout.strip()} - {dt.strftime('%Y/%m/%d')} at {dt.strftime('%H:%M:%S')}')
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
            (Path(shared.latticePath) / '.gitignore').write_text('# Store any custom .mat lattice files in this folder.')
        if shared.elements is None:
            formattedLatticePath = Path(shared.latticePath)
            fullPathName = ''
            files = sorted(list(formattedLatticePath.glob('*.mat')))
            if files:
                if latticeName == '':
                    print(f'A lattice name was not specified as an additional argument in the CLI. Loading the first alphabetical lattice \'{files[0]}\'.')
                    shared.lattice = latticeutils.LoadLattice(files[0])
                    fullPathName = files[0]
                else:
                    latticeName = latticeName.split('.')[0] + '.mat' # ensure correct file extension
                    try:
                        fullPathName = os.path.join(formattedLatticePath, latticeName)
                        shared.lattice = latticeutils.LoadLattice(fullPathName)
                    except:
                        print(f'No saved lattices were found with the name \'{latticeName}\'. Defaulting to first alphabetical lattice \'{files[0]}\'.')
                        shared.lattice = latticeutils.LoadLattice(files[0])
                        fullPathName = files[0]
                shared.latticePath = fullPathName
                shared.elements = latticeutils.GetLatticeInfo(shared.lattice)
                shared.names = [a + f' [{shared.elements.Type[b]}] (Index: {str(b)}) @ {shared.elements['s (m)'].iloc[b]:.2f} m' for a, b in zip(shared.elements.Name, shared.elements.Index)]
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

        for col in range(1, 7):
            self.page.layout().setColumnStretch(col, 1)
        self.page.layout().setColumnStretch(7, 0)
        self.page.layout().setColumnStretch(8, 0)

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
        self.inspector.setMaximumWidth(475)
        self.page.setStyleSheet(style.Dark01())
        quickSettings = QWidget()
        quickSettings.setStyleSheet(style.WidgetStyle(color = '#1e1e1e'))
        quickSettings.setMaximumWidth(475)
        quickSettings.setLayout(QGridLayout())
        quickSettings.layout().setContentsMargins(0, 0, 0, 0)
        quickSettings.layout().setSpacing(1)
        self.physicsEngine = QLabel(f'Physics Engine:\tPyAT {at.__version__} (Python Accelerator Toolbox)')
        self.physicsEngine.setFixedHeight(20)
        quickSettings.layout().addWidget(self.physicsEngine, 0, 0, 1, 1)
        self.CPU = get_cpu_info()['brand_raw']
        if 'processor' in self.CPU.lower():
            self.CPU = ' '.join(self.CPU.split(' ')[:-2])
        self.CPUName = QLabel(f'CPU:\t\t{self.CPU}')
        self.CPUName.setFixedHeight(20)
        self.CPUName.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        quickSettings.layout().addWidget(self.CPUName, 1, 0, 1, 1)
        self.physicalCPUCores = psutil.cpu_count(logical = False)
        self.logicalCPUCores = psutil.cpu_count(logical = True)
        self.CPUCoreCount = QLabel(f'CPU Cores:\t{self.physicalCPUCores} ({self.logicalCPUCores} logical processors)')
        self.CPUCoreCount.setFixedHeight(20)
        self.CPUCoreCount.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        quickSettings.layout().addWidget(self.CPUCoreCount, 2, 0, 1, 1)
        self.GPUUseage = QLabel('')
        self.GPUUseage.setFixedHeight(20)
        quickSettings.layout().addWidget(self.GPUUseage, 3, 0, 1, 1)
        self.RAMUseage = QLabel('')
        self.RAMUseage.setFixedHeight(20)
        quickSettings.layout().addWidget(self.RAMUseage, 4, 0, 1, 1)
        self.diskUseage = QLabel('')
        self.diskUseage.setFixedHeight(20)
        quickSettings.layout().addWidget(self.diskUseage, 5, 0, 1, 1)
        self.resourceMonitor = ResourceMonitor()
        self.resourceMonitor.GPUSignal.connect(self.GPUUseage.setText)
        self.resourceMonitor.RAMSignal.connect(self.RAMUseage.setText)
        self.resourceMonitor.diskSignal.connect(self.diskUseage.setText)
        #### FOR TESTING ####
        Thread(target = self.resourceMonitor.FetchResourceValues).start()
        self.page.layout().addWidget(quickSettings, 1, 7, 1, 2)
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
        shared.activeEditor.setFocus()

        # Load in settings if they exist and apply to existing entities, and create new ones if they don't already exist.
        self.setWindowOpacity(0)
        self.setEnabled(False)
        self.showMaximized()
        print('Loading settings from:', settingsPath)
        Load(settingsPath)
        def DisplayWindow():
            self.setWindowOpacity(1)
            self.setEnabled(True)
        QTimer.singleShot(1500, lambda: DisplayWindow())
    
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
            self.physicsEngine.setStyleSheet(style.WidgetStyle(color = 'green', fontColor = '#c4c4c4'))
            self.toggleDarkModeButton.setText('\u26AA Light Mode')
        else:
            self.page.setStyleSheet(style.Light01())
            self.physicsEngine.setStyleSheet(style.WidgetStyle(color = 'green', fontColor = '#c4c4c4'))
            self.toggleDarkModeButton.setText('\u26AB Dark Mode')
        shared.app.processEvents()

    def closeEvent(self, event):
        print('* Closing App *')
        shared.workspace.assistant.PushMessage('Closing app and cleaning up.')
        time.sleep(.2)
        shared.stopCleanUpTimer = True
        self.resourceMonitor.stopEvent.set()
        StopAllActions()
        if not self.quitShortcutPressed:
            Save()
        if hasattr(self, 'future') and self.future and not self.future.done():
            self.future.cancel()

if __name__ == "__main__":
    shared.app = QApplication(sys.argv)
    shared.app.setStyle(QStyleFactory.create('Fusion'))
    # skip first arg which is app name.
    window = MainWindow(*sys.argv[1:])
    qasync.run(window.ConfigureLoop())