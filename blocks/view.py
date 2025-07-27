from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QGraphicsLineItem, QLabel, QMenu, QSpacerItem, QGridLayout, QGraphicsProxyWidget, QSizePolicy, QPushButton, QVBoxLayout, QHBoxLayout, QComboBox
from PySide6.QtCore import Qt, QPointF, QPoint, QLineF, QTimer
from PySide6.QtGui import QPen, QColor
from ..draggable import Draggable
from ..ui.runningcircle import RunningCircle
from .socket import Socket
from .. import shared
from .. import style

class View(Draggable):
    '''Displays the data of arbitrary blocks.'''
    def __init__(self, parent, proxy: QGraphicsProxyWidget, name, size = (550, 440)):
        super().__init__(proxy, size)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.parent = parent
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.settings['name'] = name
        self.active = False
        self.hovering = False
        self.startPos = None
        self.linksIn = dict()
        self.Push()

    def Push(self):
        super().Push()
        self.main = QWidget()
        self.main.setLayout(QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget()
        self.widget.setObjectName('view')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(0, 0, 0, 0)
        self.widget.layout().setSpacing(0)
        # Header
        header = QWidget()
        header.setStyleSheet(style.WidgetStyle(color = "#7351C1", borderRadiusTopLeft = 8, borderRadiusTopRight = 8))
        header.setFixedHeight(40)
        header.setLayout(QHBoxLayout())
        header.layout().setContentsMargins(15, 0, 15, 0)
        self.title = QLabel(f'{self.settings['name']} (Empty)')
        header.layout().addWidget(self.title)
        # Running
        self.runningCircle = RunningCircle()
        self.runningCircle.CreateTimer()
        header.layout().addWidget(self.runningCircle, alignment = Qt.AlignRight)
        # Add header to layout
        self.widget.layout().addWidget(header)
        # Output socket
        # self.outputSocketHousing = QWidget()
        # self.outputSocketHousing.setLayout(QHBoxLayout())
        # self.outputSocketHousing.layout().setContentsMargins(0, 0, 0, 0)
        # self.outputSocketHousing.setFixedSize(50, 50)
        # self.outputSocket = Socket(self, 'M', 50, 25, 'right', 'Output')
        # self.outputSocketHousing.layout().addWidget(self.outputSocket)
        # self.layout().addWidget(self.outputSocketHousing)
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)) # for spacing
        self.main.layout().addWidget(self.widget)
        # Data socket
        self.dataSocketHousing = QWidget()
        self.dataSocketHousing.setLayout(QHBoxLayout())
        self.dataSocketHousing.layout().setContentsMargins(0, 0, 0, 0)
        self.dataSocketHousing.setFixedSize(50, 50)
        self.dataSocket = Socket(self, 'F', 50, 25, 'left', 'data', acceptableTypes = [shared.blockTypes['Orbit Response'], shared.blockTypes['BPM']])
        self.dataSocketHousing.layout().addWidget(self.dataSocket)
        self.layout().addWidget(self.dataSocket)
        self.layout().addWidget(self.main)
        self.UpdateColors()

    def UpdateColors(self):
        if not self.active:
            print('Applying base styling')
            self.BaseStyling()
            return
        self.SelectedStyling()

    def BaseStyling(self):
        if shared.lightModeOn:
            self.widget.setStyleSheet(f'''
            QWidget#view {{
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
            QWidget#view {{
            background-color: #2e2e2e;
            border: none;
            border-radius: 12px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 0px;
            }}
            ''')
            self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 14, fontColor = '#c4c4c4'))

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