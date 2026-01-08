from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QSizePolicy, QHBoxLayout, QVBoxLayout, QSpacerItem
from PySide6.QtCore import Qt, QTimer
import numpy as np
import time
from xopt.vocs import VOCS
from xopt.evaluator import Evaluator
from xopt.generators.bayesian import UpperConfidenceBoundGenerator
from xopt import Xopt
from concurrent.futures import ThreadPoolExecutor
from ..draggable import Draggable
from ...ui.runningcircle import RunningCircle
from ...actions.offline.singletaskgp import SingleTaskGPAction as OfflineAction
from ...actions.online.singletaskgp import SingleTaskGPAction as OnlineAction
from ... import style
from ... import shared
from ...utils import cothread
from ...utils.multiprocessing import PerformAction, TogglePause, StopAction

class SingleTaskGP(Draggable):
    def __init__(self, parent, proxy, **kwargs):
        super().__init__(
            proxy, name = kwargs.pop('name', 'Single Task GP'), type = 'Single Task GP', size = kwargs.pop('size', [600, 500]), 
            components = {
                'value': dict(name = 'Value', value = 0, min = 0, max = 100, default = 0, units = '', valueType = float),
            },
            **kwargs
        )
        self.timeBetweenPolls = 1000
        self.runningCircle = RunningCircle()
        self.offlineAction = OfflineAction(self)
        self.onlineAction = OnlineAction(self)
        self.header = QWidget()
        self.header.setFixedHeight(40)
        self.header.setLayout(QHBoxLayout())
        self.header.layout().setContentsMargins(15, 0, 5, 0)
        self.title = QLabel(f'{self.settings['name']} (Empty)', alignment = Qt.AlignCenter)
        self.header.layout().addWidget(self.title, alignment = Qt.AlignLeft)
        self.header.layout().addWidget(self.runningCircle, alignment = Qt.AlignRight)
        self.AddSocket('decision', 'F', 'Decision', 175, acceptableTypes = ['PV', 'Corrector', 'SVD', 'Add', 'Subtract'])
        self.AddSocket('objective', 'F', 'Objective', 185, acceptableTypes = ['PV', 'BPM', 'Add', 'Subtract'])
        self.AddSocket('kernel', 'F', 'Kernel', 175, acceptableTypes = ['Kernel', 'Linear Kernel', 'Anisotropic Kernel', 'Periodic Kernel', 'RBF Kernel'])
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
            'raw': lambda: {
                'ax': ['Decisions'],
                'names': [[d.name for d in self.decisions],
                          [f'Measurement {r + 1}' for r in range(len(self.X.data))]],
                'data': self.X.data[:, :len(self.decisions) + 1].to_numpy(),
            } if hasattr(self, 'X') and self.X.data is not None else {
                'ax': [],
                'names': [],
                'data': np.zeros(0,),
            },
            'default': lambda **kwargs: {
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

    def Pause(self):
        TogglePause(self, True)
        shared.workspace.assistant.PushMessage(f'{self.name} action is paused.')

    def Stop(self):
        StopAction(self)

    def Push(self):
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

    def Start(self, **kwargs):
        steps = kwargs.get('steps', 10)
        initialSamples = kwargs.get('initialSamples', 1)
        numParticles = kwargs.get('numParticles', 100000)
        self.decisions = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'decision']
        self.objectives = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'objective']
        # this will be deprecated soon
        independents = [
            {'ID': d.ID, 'stream': self.streamTypesIn[d.ID]} for d in self.decisions
        ]
        waiting = False
        actionToRun = self.offlineAction if not self.online else self.onlineAction
        for decision in self.decisions:
            if decision.type not in self.pvBlockTypes and np.isinf(decision.streams[self.streamTypesIn[decision.ID]]()['data']).any():
                waiting = True
                self.title.setText(f'{self.title.text().split(' (')[0]} (Waiting)')
                actionToRun.ReadDependents(independents)
                break

        def WaitUntilInputsRead():
            nonlocal initialSamples, numParticles, waiting
            if waiting:
                if not actionToRun.resultsWritten:
                    return QTimer.singleShot(actionToRun.timeBetweenPolls, WaitUntilInputsRead)
                waiting = False
                return QTimer.singleShot(actionToRun.timeBetweenPolls, WaitUntilInputsRead)
            else:
                #     return
                if not actionToRun.CheckForValidInputs():
                    return

                independentsToSet = {
                    d.ID: d.streams[self.streamTypesIn[d.ID]]() for d in self.decisions
                }
                
                counter = 0
                    
                def PerformActionAndWait(inDict:dict):
                    '''Called on a separate worker thread so will not block the UI thread.'''
                    nonlocal counter, actionToRun
                    # Set the values of the decisions
                    actionToRun.SetIndependents(independentsToSet, inDict)
                    # crank the handle
                    PerformAction(
                        self,
                        # Raw data held by the GP block will be output from tracking simulations
                        np.empty((6, numParticles, len(shared.lattice), 1)),
                        numSteps = steps,
                        currentStep = counter,
                        numParticles = numParticles,
                    )
                    while np.isinf(self.data).any():
                        time.sleep(self.timeBetweenPolls / 1e3)

                    counter += 1
                    # Read the value of the objective by feeding this GP's data upstream
                    actionToRun.ReadDependents([{'ID': self.objectives[0].ID, 'stream': self.streamTypesIn[self.objectives[0].ID]}], self.data)

                    while not actionToRun.resultsWritten:
                        time.sleep(self.timeBetweenPolls / 1e3)

                    return {'f': self.objectives[0].streams[self.streamTypesIn[self.objectives[0].ID]]()['data']}
                    
                variables = dict()
                for d in self.decisions:
                    stream = d.streams[self.streamTypesIn[d.ID]]()
                    for dim in range(stream['data'].shape[0]): # each row is a new singular vector for SVD, otherwise a 1x1 for a PV.
                        variables[f'{d.ID}-{dim}'] = [-3, 3] # values get sent through tanh so restrict to sensible domain

                vocs = VOCS(
                    variables = variables,
                    objectives = {'f': 'MINIMIZE'},
                )
                executor = ThreadPoolExecutor(max_workers = 1)
                evaluator = Evaluator(function = PerformActionAndWait)
                generator = UpperConfidenceBoundGenerator(vocs = vocs)
                self.X = Xopt(evaluator = evaluator, generator = generator, vocs = vocs)

                totalSamples = steps + initialSamples
                job = executor.submit(self.X.random_evaluate, initialSamples)

                def StepUntilComplete():
                    '''Steps through optimisation steps until finish criterion satisfied.'''
                    if len(self.X.data) < totalSamples:
                        print(f'On step {len(self.X.data) - initialSamples + 1}/{steps}')
                        self.X.data.to_csv(shared.cwd + f'\\datadump\\{self.name}.csv', index = False)
                        job = executor.submit(self.X.step)
                        job.add_done_callback(lambda _: StepUntilComplete())
                    else:
                        # temporarily save the data automatically here
                        self.X.data.to_csv(shared.cwd + f'\\datadump\\{self.name}.csv', index = False)
                        QTimer.singleShot(0, lambda: executor.shutdown(wait = True))

                job.add_done_callback(lambda _: StepUntilComplete())
        WaitUntilInputsRead()

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

    def AddLinkIn(self, ID, socket):
        if shared.entities[ID].type == 'SVD':
            return super().AddLinkIn(ID, socket, streamTypeIn = 'evecs')
        return super().AddLinkIn(ID, socket)

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 12, fontColor = '#c4c4c4'))
            self.decisionSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.kernelSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.objectiveSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.header.setStyleSheet(style.WidgetStyle(color = "#B54428", borderRadiusTopLeft = 8, borderRadiusTopRight = 8))
            self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 18, fontColor = '#c4c4c4'))

    def SelectedStyling(self):
        pass