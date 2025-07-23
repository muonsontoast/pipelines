from PySide6.QtWidgets import QWidget, QLabel, QSpacerItem, QGridLayout, QGraphicsProxyWidget, QSizePolicy, QStackedLayout, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QPointF
from ..draggable import Draggable
from ..clickablewidget import ClickableWidget
from .socket import Socket
from .. import shared
from .. import style

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
        self.active = False
        self.cursorMoved = False
        self.hovering = False
        self.startPos = None
        self.linksIn = list()
        self.linksOut = list()
        self.Push()

    def Push(self):
        self.ClearLayout()
        self.widget = QWidget()
        self.widget.setObjectName('orbitResponse')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QGridLayout())
        self.widget.layout().setContentsMargins(5, 15, 0, 0)
        # Set the size
        size = self.settings.get('size', (400, 250))
        self.setFixedSize(*size)
        name = f'Orbit Response'
        self.title = QLabel(name)
        self.title.setLayout(QVBoxLayout())
        self.title.setContentsMargins(10, 0, 0, 0)
        self.title.setObjectName('title')
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.widget.layout().addWidget(self.title, 0, 1)
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 1, 1)
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
        for link in self.linksIn:
            line = link.line()
            line.setP2(self.GetSocketPos('corrector'))
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
            QWidget#orbitResponse {{
            background-color: #363636;
            border: 2px solid #3d3d3d;
            border-radius: 4px;
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