from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QLabel, QMenu, QSpacerItem, QGraphicsProxyWidget, QSizePolicy, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QPoint
import numpy as np
from .draggable import Draggable
from .socket import Socket
from .. import shared
from .. import style
from ..components.slider import SliderComponent
from ..actions.offline.orbitresponse import OrbitResponseAction
from ..ui.runningcircle import RunningCircle
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
            'repeats': dict(name = 'Repeats', value = 5, min = 1, max = 20, default = 5, units = '', valueType = int, type = SliderComponent)
        }
        self.active = False
        self.hovering = False
        self.startPos = None
        self.offlineAction = OrbitResponseAction()
        self.runningCircle = RunningCircle()
        # Define orbit response streams
        # All streams contain a 'raw' entry for the de facto use case.
        self.streams = {
            'raw': lambda **kwargs: {
                'xlabel': 'Corrector Number',
                'ylabel': 'BPM Number',
                'xunits': '',
                'yunits': '',
                'plottype': 'imshow',
                'cmap': 'viridis',
                'cmapLabel': r'$\Delta~$mm / mrad',
                'data': self.ORM
            },
            'corrector': lambda **kwargs: {
                'xlabel': f'Corrector Kick Angle',
                'ylabel': f'Beam Center in BPM',
                'xunits': 'mrad',
                'yunits': 'mm',
                'plottype': 'scatter',
                # testing ...
                'data': np.array([(np.arange(0, self.settings['components']['steps']['value'], 1) - int(self.settings['components']['steps']['value'] / 2)) * self.settings['components']['current']['value'], 1e3 * np.mean(self.data, axis = 3)[0][0]])
            }
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
        self.CreateSection('steps', '# Steps', 3, 0)
        # BPM Repeats ...
        self.CreateSection('repeats', '# BPM measurements (0.2s wait)', 19, 0)
        # Some padding
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.AddSocket('corrector', 'F', 'Correctors', 175, acceptableTypes = ['Corrector'])
        self.AddSocket('BPM', 'F', 'BPMs', 145, acceptableTypes = ['BPM'])
        # Add orbit response widget to layout
        self.main.layout().addWidget(self.widget)
        self.AddSocket('out', 'M')
        self.AddButtons()
        super().Push()
        # Update colors
        self.UpdateColors()

    def Start(self):
        global toggleState
        if not self.online:
            self.offlineAction.correctors = self.correctors
            self.offlineAction.BPMs = self.BPMs
            if not self.offlineAction.CheckForValidInputs():
                return
            onlineText = 'online' if self.online else 'offline'
            shared.workspace.assistant.PushMessage(f'Running orbit response measurement ({onlineText}).')
            numBPMs = len(self.BPMs.keys())
            numCorrectors = len(self.correctors.keys())
            if not PerformAction(
                self,
                # empty array
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
        else:
            pass

    def Pause(self):
        TogglePause(self, True)
        shared.workspace.assistant.PushMessage(f'{self.name} action is paused.')

    def Stop(self):
        StopAction(self)

    def CleanUp(self):
        # remove the data from memory to stop it persisting after closing the application.
        self.dataSharedMemory.unlink()
        self.ORMSharedMemory.unlink()

    def CreateSection(self, name, title, sliderSteps, floatdp, disableValue = False):
        housing = QWidget()
        housing.setLayout(QHBoxLayout())
        housing.layout().setContentsMargins(15, 20, 15, 0)
        title = QLabel(title)
        title.setStyleSheet(style.LabelStyle(padding = 0, fontColor = '#c4c4c4'))
        housing.layout().addWidget(title)
        self.widget.layout().addWidget(housing, alignment = Qt.AlignLeft)
        widget = QWidget()
        widget.setFixedHeight(50)
        widget.setLayout(QVBoxLayout())
        widget.layout().setContentsMargins(15, 10, 15, 0)
        setattr(self, name, QListWidget())
        v = getattr(self, name)
        widget.layout().addWidget(v)
        v.setFocusPolicy(Qt.NoFocus)
        v.setSelectionMode(QListWidget.NoSelection)
        v.setStyleSheet(style.InspectorSectionStyle())
        setattr(self, f'{name}Amount', SliderComponent(self, f'{name}', sliderSteps, floatdp, hideRange = True, paddingBottom = 5, sliderOffset = 0, sliderRowSpacing = 15))
        amount = getattr(self, f'{name}Amount')
        if disableValue:
            amount.value.setEnabled(False)
        amount.setMaximumWidth(320)
        item = QListWidgetItem()
        item.setSizeHint(amount.sizeHint())
        v.addItem(item)
        v.setItemWidget(item, amount)
        self.widget.layout().addWidget(widget)

    def SwitchMode(self):
        if self.online:
            self.modeTitle.setText('Mode: <u><span style = "color: #C74343">Offline</span></u>')
        else:
            self.modeTitle.setText('Mode: <u><span style = "color: #3C9C29">Online</span></u>')
        self.online = not self.online

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

    def RemoveLinkIn(self, ID):
        if shared.entities[ID].type == 'BPM':
            self.BPMs.pop(ID)
        else:
            self.correctors.pop(ID)
        super().RemoveLinkIn(ID)

    def ToggleStyling(self):
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