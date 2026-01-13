from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QLabel, QMenu, QSpacerItem, QGraphicsProxyWidget, QSizePolicy, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QPoint
import numpy as np
from copy import deepcopy
from .draggable import Draggable
from .pv import PV
from .. import shared
from .. import style
from ..components.slider import SliderComponent
from ..actions.offline.orbitresponse import OrbitResponseAction
from ..ui.runningcircle import RunningCircle
from ..utils import cothread
from ..utils.multiprocessing import PerformAction, TogglePause, StopAction

'''
Orbit Response Block handles orbit response measurements off(on)line. It has two F sockets, one for Correctors, one for BPMs. 
It can take an arbitrary number of both correctors and BPMs and run through the routine to generate individual response matrices 
for each of the correctors, accounting for each BPM and corrector setting. A full ORM is also generated. The block's M socket can be extended
to save the data, or for further processing in a pipeline.
'''

class OrbitResponse(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'Orbit Response'), type = 'Orbit Response', size = kwargs.pop('size', [575, 440]), **kwargs)
        self.parent = parent
        self.correctors = dict()
        self.BPMs = dict()
        self.ORM = np.empty((0,))
        self.setStyleSheet('background: none')
        self.settings['components'] = {
            'current': dict(name = 'Current', value = .5, min = .01, max = 5, default = .5, units = 'mrad', type = SliderComponent),
            'steps': dict(name = 'Steps', value = 3, min = 3, max = 9, default = 3, units = 'mrad', valueType = int, type = SliderComponent),
            'repeats': dict(name = 'Repeats', value = 1, min = 1, max = 20, default = 1, units = '', valueType = int, type = SliderComponent)
        }
        self.active = False
        self.hovering = False
        self.startPos = None
        self.offlineAction = OrbitResponseAction(self)
        self.runningCircle = RunningCircle()
        self.streams = {
            'raw': lambda: {
                # Axis names
                'ax': ['BPM', 'Corrector', 'Step (mrad)'],
                # Names of each item in the respective axes
                'names': [[b.name for b in self.BPMs.values()],
                          [c.name for c in self.correctors.values()],
                          [str(s) for s in self.settings['components']['current']['value'] * (np.array(range(self.settings['components']['steps']['value'])) - int(self.settings['components']['steps']['value'] / 2))],
                          [f'Measurement {r + 1}' for r in range(self.settings['components']['repeats']['value'])]],
                'defaults': {
                    c.ID: c.streams[self.streamTypesIn[c.ID]]()['default'] for c in self.correctors.values()
                },
                'lims': {
                    c.ID: c.streams[self.streamTypesIn[c.ID]]()['lims'] for c in self.correctors.values()
                },
                'linkedIdxs': {
                    c.ID: c.streams[self.streamTypesIn[c.ID]]()['linkedIdx'] for c in self.correctors.values()
                },
                'alignments': {
                    c.ID: c.streams[self.streamTypesIn[c.ID]]()['alignments'] for c in self.correctors.values()
                },
                'data': self.data,
            },
            'default': lambda: {
                'xlabel': 'Corrector Number',
                'ylabel': 'BPM Number',
                'xticks': np.arange(len(self.correctors)),
                'yticks': np.arange(len(self.BPMs)),
                'xticklabels': [c.name for c in self.correctors.values()],
                'yticklabels': [b.name for b in self.BPMs.values()],
                'xunits': '',
                'yunits': '',
                'plottype': 'imshow',
                'cmap': 'viridis',
                'cmapLabel': r'$\Delta~$mm / mrad',
                'data': self.ORM
            },
        }
        shared.runnableBlocks[self.ID] = self
        self.Push()

    def Push(self):
        self.widget = QWidget()
        self.widget.setObjectName('orbitResponse')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(0, 0, 0, 0)
        self.widget.layout().setSpacing(0)
        # Header
        header = QWidget()
        header.setStyleSheet(style.WidgetStyle(color = "#2867B5", borderRadiusTopLeft = 8, borderRadiusTopRight = 8))
        header.setFixedHeight(40)
        header.setLayout(QHBoxLayout())
        header.layout().setContentsMargins(15, 0, 5, 0)
        self.title = QLabel(f'{self.settings['name']} (Empty)', alignment = Qt.AlignCenter)
        header.layout().addWidget(self.title)
        # Running
        header.layout().addWidget(self.runningCircle, alignment = Qt.AlignRight)
        # Add header to layout
        self.widget.layout().addWidget(header)
        # On/off-line
        self.mode = QWidget()
        self.mode.setLayout(QHBoxLayout())
        self.mode.layout().setContentsMargins(15, 10, 15, 0)
        self.modeTitle = QLabel('Mode: <u><span style = "color: #C74343">Offline</span></u>')
        self.modeTitle.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', padding = 0))
        self.modeTitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.modeSwitch = QPushButton('Switch')
        self.modeSwitch.clicked.connect(self.SwitchMode)
        self.modeSwitch.setStyleSheet(style.PushButtonStyle(color = '#1e1e1e', fontColor = '#c4c4c4', padding = 5))
        self.modeSwitch.setFixedWidth(100)
        self.mode.layout().addWidget(self.modeTitle)
        self.mode.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.mode.layout().addWidget(self.modeSwitch)
        self.widget.layout().addWidget(self.mode)
        # Fit order
        self.order = QWidget()
        self.order.setLayout(QHBoxLayout())
        self.order.layout().setContentsMargins(15, 10, 15, 0)
        self.orderTitle = QLabel('Fit (least squares)')
        self.orderTitle.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', padding = 0))
        self.orderMenu = QMenu()
        self.orderOptions = QPushButton('Linear        \u25BC')
        self.orderOptions.setStyleSheet(style.PushButtonStyle(color = '#1e1e1e', fontColor = '#c4c4c4', padding = 5, textAlign = 'right'))
        self.orderOptions.setFixedWidth(115)
        self.orderOptions.clicked.connect(self.ShowMenu)
        self.orderMenu.addAction('Linear', self.SetOrderLinear)
        self.orderMenu.addAction('Quadratic', self.SetOrderQuadratic)
        self.order.layout().addWidget(self.orderTitle)
        self.order.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.order.layout().addWidget(self.orderOptions)
        self.widget.layout().addWidget(self.order)
        # # Corrector step current / kick
        self.CreateSection('current', 'Kick / step (mrad)', 1e6, 3)
        # Corrector steps
        self.CreateSection('steps', 'Steps', 3, 0)
        # BPM Repeats ...
        self.CreateSection('repeats', 'BPM measurements (0.2s wait)', 19, 0)
        # Some padding
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.AddSocket('corrector', 'F', 'Correctors', 175, acceptableTypes = [PV])
        self.AddSocket('BPM', 'F', 'BPMs', 145, acceptableTypes = [PV])
        # Add orbit response widget to layout
        self.main.layout().addWidget(self.widget)
        self.AddSocket('out', 'M')
        self.AddButtons()
        super().Push()
        # Update colors
        self.UpdateColors()

    def Start(self, setpoint:np.ndarray = None, **kwargs):
        # The ORM is assumed fixed for a given beamline so passing a setpoint, sets all connected correctors.
        self.offlineAction.resultsWritten = False
        print('Starting ORM')
        # Sort the correctors and BPMs to produce a proper ORM (Index -> Alignment)
        self.correctors = dict(sorted(sorted(self.correctors.items(), key = lambda item: item[1].settings['linkedElement'].Index), key = lambda item: item[1].settings['alignment']))
        self.BPMs = dict(sorted(sorted(self.BPMs.items(), key = lambda item: item[1].settings['linkedElement'].Index), key = lambda item: item[1].settings['alignment']))
        if not self.online:
            self.offlineAction.correctors = self.correctors
            self.offlineAction.BPMs = self.BPMs
            self.offlineAction.lattice = deepcopy(shared.lattice)
            if not self.offlineAction.CheckForValidInputs():
                return
            onlineText = 'offline'
            shared.workspace.assistant.PushMessage(f'Running orbit response measurement ({onlineText}).')
            numBPMs = len(self.BPMs.keys())
            numCorrectors = len(self.correctors.keys())
            # Invoke Start() methods of children to generate data
            if not PerformAction(
                self,
                np.empty((numBPMs, numCorrectors,
                self.settings['components']['steps']['value'],
                self.settings['components']['repeats']['value'])),
                postProcessedDataName = 'ORM',
                emptyPostProcessedDataArray = np.empty((numBPMs, numCorrectors)),
                numSteps = self.settings['components']['steps']['value'],
                stepKick = self.settings['components']['current']['value'],
                repeats = self.settings['components']['repeats']['value'],
                getRawData = False,
            ):
                shared.workspace.assistant.PushMessage('Orbit response measurement already running.', 'Error')

    def Pause(self):
        TogglePause(self, True)
        shared.workspace.assistant.PushMessage(f'{self.name} action is paused.')

    def Stop(self):
        StopAction(self)

    def CleanUp(self):
        # remove the data from memory to stop it persisting after closing the application.
        self.dataSharedMemory.unlink()
        self.ORMSharedMemory.unlink()

    def SwitchMode(self):
        if cothread.AVAILABLE:
            if self.online:
                self.modeTitle.setText('Mode: <u><span style = "color: #C74343">Offline</span></u>')
            else:
                self.modeTitle.setText('Mode: <u><span style = "color: #3C9C29">Online</span></u>')
            self.online = not self.online
            shared.workspace.assistant.PushMessage(f'{self.name} mode is set to {'Online' if self.online else 'Offline'}')
        else:
            shared.workspace.assistant.PushMessage(f'Online mode has been disabled because cothread is not available on your machine.', 'Warning')

    def SetOrderLinear(self):
        self.orderOptions.setText('Linear        \u25BC')
    
    def SetOrderQuadratic(self):
        self.orderOptions.setText('Quadratic     \u25BC')

    def ShowMenu(self):
        position = self.orderOptions.mapToGlobal(QPoint(0, self.orderOptions.height()))
        self.orderMenu.popup(position)

    def mousePressEvent(self, event):
        self.startPos = event.pos()
        if self.canDrag or (self.hoveringSocket and self.hoveringSocket.name != 'Output'):
            super().mousePressEvent(event)
            return
        shared.PVLinkSource = self
        shared.activeSocket = self.outSocket
        super().mousePressEvent(event)

    def UpdateColors(self):
        if not self.active:
            self.BaseStyling()
            return
        self.SelectedStyling()

    def AddLinkIn(self, ID, socket):
        if shared.entities[ID].type == 'BPM':
            self.BPMs[ID] = shared.entities[ID]
        else:
            self.correctors[ID] = shared.entities[ID]
        # update canRun flag
        if self.correctors and self.BPMs:
            self.canRun = True
        super().AddLinkIn(ID, socket)
        if shared.entities[ID].type in ['Single Task GP']:
            self.streamTypesIn[ID] = 'raw'

    def RemoveLinkIn(self, ID):
        if shared.entities[ID].type == 'BPM':
            self.BPMs.pop(ID)
        else:
            self.correctors.pop(ID)
        super().RemoveLinkIn(ID)

    def ToggleStyling(self, active = None):
        pass

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.setStyleSheet(style.WidgetStyle())
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 12, fontColor = '#c4c4c4'))
            self.correctorSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.BPMSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 18, fontColor = '#c4c4c4'))

    def SelectedStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #5C5C5C;
            border: 4px solid #424242;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            ''')