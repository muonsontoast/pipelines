from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QLabel, QMenu, QSpacerItem, QGraphicsProxyWidget, QSizePolicy, QPushButton, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QPoint
import numpy as np
from .draggable import Draggable
from .socket import Socket
from .. import shared
from .. import style
from ..components.slider import SliderComponent
from ..actions.orbitresponse import OrbitResponseAction
from ..ui.runningcircle import RunningCircle
from ..utils.multiprocessing import PerformAction

'''
Orbit Response Block handles orbit response measurements off(on)line. It has two F sockets, one for Correctors, one for BPMs. 
It can take an arbitrary number of both correctors and BPMs and run through the routine to generate individual response matrices 
for each of the correctors, accounting for each BPM and corrector setting. A full ORM is also generated. The block's M socket can be extended
to save the data, or for further processing in a pipeline.
'''

class OrbitResponse(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'Orbit Response'), type = kwargs.pop('type', OrbitResponse), size = kwargs.pop('size', (550, 440)), **kwargs)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.parent = parent
        self.correctors = dict()
        self.BPMs = dict()
        self.blockType = 'Orbit Response'
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.settings['components'] = {
            'current': dict(name = 'Current', value = .5, min = .01, max = 5, default = .5, units = 'mrad', type = SliderComponent),
            'steps': dict(name = 'Steps', value = 3, min = 3, max = 9, default = 3, units = 'mrad', valueType = int, type = SliderComponent),
            'repeats': dict(name = 'Repeats', value = 5, min = 1, max = 20, default = 5, units = '', valueType = int, type = SliderComponent)
        }
        self.active = False
        self.hovering = False
        self.startPos = None
        self.action = OrbitResponseAction()
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
        self.Push()

    def Push(self):
        super().Push()
        self.main = QWidget()
        self.main.setLayout(QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)
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
        self.online = False
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
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)) # for spacing
        # Sockets
        sockets = QWidget()
        sockets.setLayout(QVBoxLayout())
        sockets.layout().setContentsMargins(0, 0, 0, 0)
        # Corrector socket
        self.correctorSocketHousing = QWidget()
        self.correctorSocketHousing.setLayout(QHBoxLayout())
        self.correctorSocketHousing.layout().setContentsMargins(0, 0, 0, 0)
        self.correctorSocketHousing.layout().setSpacing(0)
        self.correctorSocketHousing.setFixedSize(140, 50)
        self.correctorSocket = Socket(self, 'F', 50, 25, 'left', 'corrector', ['Corrector'])
        self.correctorSocketHousing.layout().addWidget(self.correctorSocket)
        correctorSocketTitle = QLabel('Correctors')
        correctorSocketTitle.setObjectName('correctorSocketTitle')
        correctorSocketTitle.setAlignment(Qt.AlignCenter)
        self.correctorSocketHousing.layout().addWidget(correctorSocketTitle)
        sockets.layout().addWidget(self.correctorSocketHousing, alignment = Qt.AlignRight)
        # BPM Socket
        self.BPMSocketHousing = QWidget()
        self.BPMSocketHousing.setLayout(QHBoxLayout())
        self.BPMSocketHousing.layout().setContentsMargins(0, 0, 0, 0)
        self.BPMSocketHousing.layout().setSpacing(0)
        self.BPMSocketHousing.setFixedSize(140, 50)
        self.BPMSocket = Socket(self, 'F', 50, 25, 'left', 'BPM', acceptableTypes = ['BPM'])
        self.BPMSocketHousing.layout().addWidget(self.BPMSocket)
        BPMSocketTitle = QLabel('BPMs')
        BPMSocketTitle.setObjectName('BPMSocketTitle')
        BPMSocketTitle.setAlignment(Qt.AlignCenter)
        self.BPMSocketHousing.layout().addWidget(BPMSocketTitle)
        sockets.layout().addWidget(self.BPMSocketHousing, alignment = Qt.AlignRight)
        # Add sockets to layout
        self.layout().addWidget(sockets)
        # Add orbit response widget to layout
        self.main.layout().addWidget(self.widget)
        # Control buttons
        self.buttons = QWidget()
        buttonsHeight = 35
        self.buttons.setFixedHeight(buttonsHeight)
        self.buttons.setLayout(QHBoxLayout())
        self.buttons.layout().setContentsMargins(15, 2, 15, 10)
        self.start = QPushButton('Start')
        self.start.setFixedHeight(buttonsHeight)
        self.start.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#1e1e1e', fontColor = '#c4c4c4'))
        self.start.clicked.connect(self.Start)
        self.pause = QPushButton('Pause')
        self.pause.setFixedHeight(buttonsHeight)
        self.pause.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#1e1e1e', fontColor = '#c4c4c4'))
        self.stop = QPushButton('Stop')
        self.stop.setFixedHeight(buttonsHeight)
        self.stop.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#1e1e1e', fontColor = '#c4c4c4'))
        self.clear = QPushButton('Clear')
        self.clear.setFixedHeight(buttonsHeight)
        self.clear.setStyleSheet(style.PushButtonStyle(padding = 0, color = '#1e1e1e', fontColor = '#c4c4c4'))
        self.buttons.layout().addWidget(self.start)
        self.buttons.layout().addWidget(self.pause)
        self.buttons.layout().addWidget(self.stop)
        self.buttons.layout().addWidget(self.clear)
        self.main.layout().addWidget(self.buttons)
        self.layout().addWidget(self.main)
        # Output socket
        self.outputSocketHousing = QWidget()
        self.outputSocketHousing.setLayout(QHBoxLayout())
        self.outputSocketHousing.layout().setContentsMargins(0, 0, 0, 0)
        self.outputSocketHousing.setFixedSize(50, 50)
        self.outputSocket = Socket(self, 'M', 50, 25, 'right', 'output')
        self.outputSocketHousing.layout().addWidget(self.outputSocket)
        self.layout().addWidget(self.outputSocketHousing)
        # Update colors
        self.UpdateColors()

    # data can be visualised many ways
    # there should be a record of the differnt ways of visualising, as well as instructions for how to do so.
    # the view block will automatically know how to follow these instructions.
    # blocks that are fed the output of a block holding data, will know which option to pick.

    def Start(self):
        self.action.correctors = self.correctors
        self.action.BPMs = self.BPMs
        if not self.action.CheckForValidInputs():
            return
        onlineText = 'online' if self.online else 'offline'
        shared.workspace.assistant.PushMessage(f'Running orbit response measurement ({onlineText}).')
        print('Starting orbit response measurement')
        self.runningCircle.Start()
        self.title.setText('Orbit Response (Running)')
        PerformAction(
            self,
            self.online,
            self.settings['components']['steps']['value'],
            self.settings['components']['current']['value'],
            self.settings['components']['repeats']['value'],
            getRawData = False,
            postProcessedData = 'ORM'
            )

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
        shared.activeSocket = self.outputSocket
        super().mousePressEvent(event)

    def UpdateColors(self):
        if not self.active:
            self.BaseStyling()
            return
        self.SelectedStyling()

    def RemoveLinkIn(self, ID):
        if shared.entities[ID].name == 'BPM':
            self.BPMs.pop(ID)
        else:
            self.correctors.pop(ID)
        super().RemoveLinkIn(ID)

    def ToggleStyling(self):
        pass

    def BaseStyling(self):
        if shared.lightModeOn:
            self.widget.setStyleSheet(f'''
            QWidget#orbitResponse {{
            background-color: #D2C5A0;
            border: 2px solid #B5AB8D;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 0px;
            }}
            ''')
        else:
            "#282828"
            self.widget.setStyleSheet(f'''
            QWidget#orbitResponse {{
            background-color: #2e2e2e;
            border: none;
            border-radius: 12px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 0px;
            }}
            ''')
            self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 18, fontColor = '#c4c4c4'))
            self.correctorSocketHousing.setStyleSheet(f'''
            QWidget#correctorSocketTitle {{
            background-color: #2e2e2e;
            color: #c4c4c4;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            ''')
            self.BPMSocketHousing.setStyleSheet(f'''
            QWidget#BPMSocketTitle {{
            background-color: #2e2e2e;
            color: #c4c4c4;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            ''')

    def SelectedStyling(self):
        if shared.lightModeOn:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #ECDAAB;
            border: 4px solid #DCC891;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            ''')
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