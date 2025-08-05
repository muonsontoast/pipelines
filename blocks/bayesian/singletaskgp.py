from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QSizePolicy, QHBoxLayout, QVBoxLayout, QSpacerItem
from PySide6.QtCore import Qt
import numpy as np
from ..draggable import Draggable
from ...ui.runningcircle import RunningCircle
from ...actions.offline.singletaskgp import SingleTaskGPAction as OfflineAction
from ...actions.online.singletaskgp import SingleTaskGPAction as OnlineAction
from ... import style
from ... import shared
from ...utils.multiprocessing import PerformAction, TogglePause, StopAction

class SingleTaskGP(Draggable):
    def __init__(self, parent, proxy, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'Single Task GP'), type = 'Single Task GP', size = kwargs.pop('size', [600, 500]), **kwargs)
        self.runningCircle = RunningCircle()
        self.offlineAction = OfflineAction()
        self.onlineAction = OnlineAction()
        # Header
        self.header = QWidget()
        self.header.setFixedHeight(40)
        self.header.setLayout(QHBoxLayout())
        self.header.layout().setContentsMargins(15, 0, 5, 0)
        self.title = QLabel(f'{self.settings['name']} (Empty)', alignment = Qt.AlignCenter)
        self.header.layout().addWidget(self.title, alignment = Qt.AlignLeft)
        self.header.layout().addWidget(self.runningCircle, alignment = Qt.AlignRight)
        self.AddSocket('decision', 'F', 'Decisions', 175, acceptableTypes = ['PV', 'Corrector'])
        self.AddSocket('objective', 'F', 'Objective', 185, acceptableTypes = ['PV', 'BPM'])
        self.AddSocket('context', 'F', 'Context', 175, acceptableTypes = ['PV', 'Corrector', 'BPM'])
        self.AddSocket('out', 'M')
        # Main widget
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(0, 0, 0, 0)
        self.widget.layout().setSpacing(0)
        # Content widget inside main
        self.content = QWidget()
        self.content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content.setLayout(QVBoxLayout())
        self.content.layout().setSpacing(0)

        self.streams = {
            'raw': lambda **kwargs: {
                'xlabel': 'Step',
                'xlim': [0, len(self.data) - 1],
                'ylabel': f'{kwargs.get('ylabel', 'Objective')}',
                'ylim': [-5, 5],
                'xunits': '',
                'yunits': '',
                'plottype': 'plot',
                'data': self.data
            },
        }
        shared.runnableBlocks[self.ID] = self

        self.Push()
        self.ToggleStyling(active = False)
        print(f'{self.name}\'s data looks like this on creation:', self.data)

    def Pause(self):
        TogglePause(self, True)
        shared.workspace.assistant.PushMessage(f'{self.name} action is paused.')

    def Stop(self):
        StopAction(self)

    def Push(self):
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
        self.widget.layout().addWidget(self.header)
        self.content.layout().addWidget(self.mode)
        self.content.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.widget.layout().addWidget(self.content)
        self.main.layout().addWidget(self.widget)
        self.AddButtons()

        super().Push()

    def Start(self):
        steps = 50
        initialSamples = 0
        if self.online:
            self.onlineAction.decisions = {shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'decision'}
            self.onlineAction.objectives = {shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'objective'}
            if not self.onlineAction.CheckForValidInputs():
                return
            PerformAction(
                self,
                np.empty(steps + 1),
                numSteps = steps,
                initialSamples = initialSamples,
                goal = 'MAXIMIZE',
            )
            shared.workspace.assistant.PushMessage(f'Running single objective optimisation with {len(self.onlineAction.decisions)} decision variable(s) (online).')
        else:
            self.offlineAction.decisions = {shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'decision'}
            self.offlineAction.objectives = {shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'objective'}
            if not self.offlineAction.CheckForValidInputs():
                return
            PerformAction(
                self,
                np.empty(steps + 1),
                numSteps = steps,
                initialSamples = initialSamples,
            )
            shared.workspace.assistant.PushMessage(f'Running single objective optimisation with {len(self.offlineAction.decisions)} decision variable(s) (offline).')

    def SwitchMode(self):
        if self.online:
            self.modeTitle.setText('Mode: <u><span style = "color: #C74343">Offline</span></u>')
        else:
            self.modeTitle.setText('Mode: <u><span style = "color: #3C9C29">Online</span></u>')
        self.online = not self.online

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 12, fontColor = '#c4c4c4'))
            self.decisionSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.contextSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.objectiveSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.header.setStyleSheet(style.WidgetStyle(color = "#B54428", borderRadiusTopLeft = 8, borderRadiusTopRight = 8))
            self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 18, fontColor = '#c4c4c4'))

    def SelectedStyling(self):
        pass