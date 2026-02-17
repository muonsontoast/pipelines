from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QSizePolicy, QGraphicsProxyWidget
from PySide6.QtCore import Qt
import numpy as np
from .filter import Filter
from ..draggable import Draggable
from ... import shared
from ... import style

class Control(Filter):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(
            parent, 
            proxy,
            name = kwargs.pop('name', 'Control'),
            type = kwargs.pop('type', 'Control'),
            size = kwargs.pop('size', [415, 200]),
            fontsize = kwargs.pop('fontsize', 12),
            onControl = kwargs.pop('onControl', False),
            **kwargs,
        )
        self.inLink = None

    def Start(self):
        if self.inLink is None:
            return np.nan
        if len(self.linksIn) > 1:
            allowSignalToPropagate = not self.settings['onControl']
            for ID in self.linksIn:
                if self.linksIn[ID]['socket'] == 'control':
                    data = shared.entities[ID].Start()
                    if np.isnan(data) or np.isinf(data) or data != 0:
                        allowSignalToPropagate = self.settings['onControl']
                        break
            if allowSignalToPropagate:
                return shared.entities[self.inLink].Start()
        else:
            return shared.entities[self.inLink].Start()
        return np.nan
        
    def Push(self):
        super().Push(applyStyling = False)
        self.AddSocket('control', 'F', 'Control', 160, acceptableTypes = [Draggable])
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(5, 10, 10, 10)
        self.content = QWidget()
        self.content.setLayout(QVBoxLayout())
        self.content.layout().setContentsMargins(5, 5, 5, 5)
        self.content.layout().setSpacing(15)
        self.infoLabel = QLabel('If Any Control \u2260 0:')
        self.content.layout().addWidget(self.infoLabel, alignment = Qt.AlignCenter)
        self.switch = QPushButton('Block') if not self.settings['onControl'] else QPushButton('Allow')
        self.switch.setFixedWidth(65)
        self.switch.pressed.connect(self.Switch)
        self.content.layout().addWidget(self.switch, alignment = Qt.AlignCenter)
        self.widget.layout().addWidget(self.content, alignment = Qt.AlignCenter)
        self.main.layout().addWidget(self.widget)
        self.BaseStyling()

    def Switch(self):
        self.settings['onControl'] = not self.settings['onControl']
        if self.settings['onControl']:
            shared.workspace.assistant.PushMessage(f'{self.name} now ALLOWS input signal propagation upon detecting any non-zero control signals.')
            self.switch.setText('Allow')
        else:
            shared.workspace.assistant.PushMessage(f'{self.name} now BLOCKS input signal propagation upon detecting any non-zero control signals.')
            self.switch.setText('Block')

    def AddLinkIn(self, ID, socket, streamTypeIn = '', updateGroupLinks=True, **kwargs):
        result = super().AddLinkIn(ID, socket, streamTypeIn, updateGroupLinks, **kwargs)
        if result:
            if socket == 'in':
                self.inLink = ID
        return result
    
    def RemoveLinkIn(self, ID):
        if ID == self.inLink:
            self.inLink = None
        return super().RemoveLinkIn(ID)
    
    def BaseStyling(self):
        super().BaseStyling()
        self.infoLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 14))
        self.switch.setStyleSheet(style.PushButtonStyle(color = '#2e2e2e', fontColor = '#c4c4c4', fontSize = 14, borderRadius = 6))