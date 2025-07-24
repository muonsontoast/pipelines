from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QLabel, QMenu, QSpacerItem, QGridLayout, QGraphicsProxyWidget, QSizePolicy, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox
from PySide6.QtCore import Qt, QPointF, QPoint
from PySide6.QtGui import QAction
from ..draggable import Draggable
from .socket import Socket
from ..ui.runningcircle import RunningCircle
from .. import shared
from .. import style
from ..components.slider import SliderComponent
import os

'''
Orbit Response Block handles orbit response measurements off(on)line. It has two F sockets, one for Correctors, one for BPMs. 
It can take an arbitrary number of both correctors and BPMs and run through the routine to generate individual response matrices 
for each of the correctors, accounting for each BPM and corrector setting. A full ORM is also generated. The block's M socket can be extended
to save the data, or for further processing in a pipeline.
'''

class OrbitResponse(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, name):
        super().__init__()
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.parent = parent
        self.proxy = proxy
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.settings = dict()
        self.settings['name'] = name
        self.settings['components'] = {
            'steps': dict(name = 'Steps', value = 3, min = 3, max = 9, default = 3, units = 'mrad', type = SliderComponent),
        }
        self.active = False
        self.cursorMoved = False
        self.hovering = False
        self.startPos = None
        # These need to be dicts, key = link / line item, value = socket
        self.linksIn = dict()
        self.linksOut = dict()
        self.Push()

    def Push(self):
        self.ClearLayout()
        self.widget = QWidget()
        self.widget.setObjectName('orbitResponse')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(0, 0, 0, 0)
        self.widget.layout().setSpacing(0)
        # Set the size
        size = self.settings.get('size', (500, 350))
        self.setFixedSize(*size)
        # Header
        header = QWidget()
        header.setFixedHeight(40)
        header.setLayout(QHBoxLayout())
        header.layout().setContentsMargins(15, 0, 15, 0)
        name = f'Orbit Response (Empty)'
        self.title = QLabel(name)
        self.title.setLayout(QVBoxLayout())
        self.title.layout().setContentsMargins(0, 0, 0, 0)
        self.title.setObjectName('title')
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # self.widget.layout().addWidget(self.title)
        header.layout().addWidget(self.title)
        # Running
        self.runningCircle = RunningCircle()
        self.runningCircle.CreateTimer()
        # self.widget.layout().addWidget(self.runningCircle)
        header.layout().addWidget(self.runningCircle, alignment = Qt.AlignRight)
        # Add header to layout
        self.widget.layout().addWidget(header)
        # some pad
        space = QWidget()
        space.setStyleSheet('background-color: #3d3d3d')
        space.setFixedHeight(10)
        self.widget.layout().addWidget(space)
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
        # Corrector steps
        stepsHousing = QWidget()
        stepsHousing.setLayout(QHBoxLayout())
        stepsHousing.layout().setContentsMargins(15, 20, 15, 0)
        stepsTitle = QLabel('Corrector steps (centered on 0 mrad)')
        stepsTitle.setStyleSheet(style.LabelStyle(padding = 0, fontColor = '#c4c4c4'))
        stepsHousing.layout().addWidget(stepsTitle)
        self.widget.layout().addWidget(stepsHousing, alignment = Qt.AlignLeft)
        stepsWidget = QWidget()
        stepsWidget.setFixedHeight(50)
        stepsWidget.setLayout(QVBoxLayout())
        stepsWidget.layout().setContentsMargins(15, 10, 15, 0)
        self.steps = QListWidget()
        stepsWidget.layout().addWidget(self.steps)
        self.steps.setFocusPolicy(Qt.NoFocus)
        self.steps.setSelectionMode(QListWidget.NoSelection)
        self.steps.setStyleSheet(style.InspectorSectionStyle())
        self.steps.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.steps.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.steps.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.stepsAmount = SliderComponent(self, 'steps', 3, 0, hideRange = True, paddingBottom = 5, sliderOffset = 0, sliderRowSpacing = 15)
        self.stepsAmount.setMaximumWidth(320)
        item = QListWidgetItem()
        item.setSizeHint(self.stepsAmount.sizeHint())
        self.steps.addItem(item)
        self.steps.setItemWidget(item, self.stepsAmount)
        self.widget.layout().addWidget(stepsWidget)
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
        self.correctorSocket = Socket(self, 'F', 50, 25, 'left', 'Correctors', acceptableTypes = [shared.blockTypes['Kicker'], shared.blockTypes['PV']])
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
        self.BPMSocket = Socket(self, 'F', 50, 25, 'left', 'BPMs', acceptableTypes = [shared.blockTypes['PV']])
        self.BPMSocketHousing.layout().addWidget(self.BPMSocket)
        BPMSocketTitle = QLabel('BPMs')
        BPMSocketTitle.setObjectName('BPMSocketTitle')
        BPMSocketTitle.setAlignment(Qt.AlignCenter)
        self.BPMSocketHousing.layout().addWidget(BPMSocketTitle)
        sockets.layout().addWidget(self.BPMSocketHousing, alignment = Qt.AlignRight)
        # Add sockets to layout
        self.layout().addWidget(sockets)
        # Add orbit response widget to layout
        self.layout().addWidget(self.widget)
        # Update colors
        self.UpdateColors()

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

    def GetSocketPos(self, name):
        socket = getattr(self, f'{name}Socket')
        anchor = QPointF(30, socket.rect().height() / 2) # add a small horizontal pad for display tidiness
        localPos = socket.mapTo(self.proxy.widget(), anchor)
        return self.proxy.scenePos() + localPos

    def UpdateColors(self):
        if not self.active:
            print('Applying base styling')
            self.BaseStyling()
            return
        self.SelectedStyling()

    def mousePressEvent(self, event):
        self.startPos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        for link, socket in self.linksIn.items():
            line = link.line()
            line.setP2(self.GetSocketPos(socket))
            link.setLine(line)

    def ClearLayout(self):
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

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
            QWidget#title {{
            color: #1e1e1e;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')
        else:
            self.widget.setStyleSheet(f'''
            QWidget#orbitResponse {{
            background-color: #363636;
            border: 2px solid #3d3d3d;
            border-radius: 4px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 0px;
            }}
            QWidget#title {{
            color: #c4c4c4;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')
            self.correctorSocketHousing.setStyleSheet(f'''
            QWidget#correctorSocketTitle {{
            background-color: #363636;
            color: #c4c4c4;
            border-left: 2px solid #3d3d3d;
            border-top: 2px solid #3d3d3d;
            border-right: none;
            border-bottom: 2px solid #3d3d3d;          
            border-radius: 0px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            ''')
            self.BPMSocketHousing.setStyleSheet(f'''
            QWidget#BPMSocketTitle {{
            background-color: #363636;
            color: #c4c4c4;
            border-left: 2px solid #3d3d3d;
            border-top: 2px solid #3d3d3d;
            border-right: none;
            border-bottom: 2px solid #3d3d3d;          
            border-radius: 0px;
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
            QWidget#title {{
            color: #1e1e1e;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')
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
            QWidget#title {{
            color: #c4c4c4;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            }}''')