from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QSizePolicy, QHBoxLayout, QVBoxLayout, QSpacerItem
from PySide6.QtCore import Qt, QTimer
import numpy as np
import time
from xopt.vocs import VOCS
from xopt.evaluator import Evaluator
from xopt.generators.bayesian import UpperConfidenceBoundGenerator
from xopt import Xopt, AsynchronousXopt
from concurrent.futures import ThreadPoolExecutor
import threading
from pandas import DataFrame as df
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
        self.AddSocket('decision', 'F', 'Decisions', 175, acceptableTypes = ['PV', 'Corrector', 'SVD', 'Add', 'Subtract'])
        self.AddSocket('objective', 'F', 'Objective', 185, acceptableTypes = ['PV', 'BPM', 'Add', 'Subtract'])
        self.AddSocket('context', 'F', 'Context', 175, acceptableTypes = ['PV', 'Corrector', 'BPM', 'Add', 'Subtract'])
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
        print('Starting up a Single Task GP')
        steps = kwargs.get('steps', 350)
        initialSamples = kwargs.get('initialSamples', 10)
        numParticles = kwargs.get('numParticles', 100000)
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
            )
            shared.workspace.assistant.PushMessage(f'Running single objective optimisation with {len(self.onlineAction.decisions)} decision variable(s) (online).')
        else:
            self.decisions = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'decision']
            self.objectives = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'objective']
            # this will be deprecated soon
            independents = [
                {'ID': d.ID, 'stream': self.streamTypesIn[d.ID]} for d in self.decisions
            ]
            
            waiting = False
            for decision in self.decisions:
                if decision.type not in self.pvBlockTypes and np.isinf(decision.streams[self.streamTypesIn[decision.ID]]()['data']).any():
                    waiting = True
                    self.title.setText(f'{self.title.text().split(' (')[0]} (Waiting)')
                    self.offlineAction.ReadDependents(independents)
                    break

            def WaitUntilInputsRead():
                nonlocal initialSamples, numParticles, waiting
                if waiting:
                    if not self.offlineAction.resultsWritten:
                        return QTimer.singleShot(self.offlineAction.timeBetweenPolls, WaitUntilInputsRead)
                    waiting = False
                    return QTimer.singleShot(self.offlineAction.timeBetweenPolls, WaitUntilInputsRead)
                else:
                    if not self.offlineAction.CheckForValidInputs():
                        return

                    independentsToSet = {
                        d.ID: d.streams[self.streamTypesIn[d.ID]]() for d in self.decisions
                    }
                    
                    counter = 0
                        
                    def PerformActionAndWait(inDict:dict):
                        '''Called on a separate worker thread so will not block the UI thread.'''
                        nonlocal counter
                        # Set the values of the decisions
                        self.offlineAction.SetIndependents(independentsToSet, inDict)
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
                            print(f'({counter}) Waiting...')
                            time.sleep(self.timeBetweenPolls / 1e3)

                        counter += 1
                        # Read the value of the objective by feeding this GP's data upstream
                        self.offlineAction.ReadDependents([{'ID': self.objectives[0].ID, 'stream': self.streamTypesIn[self.objectives[0].ID]}], self.data)

                        while not self.offlineAction.resultsWritten:
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
                    evaluator = Evaluator(function = PerformActionAndWait, executor = executor, max_workers = 1)
                    # evaluator = Evaluator(function = PerformActionAndWait)
                    generator = UpperConfidenceBoundGenerator(vocs = vocs)
                    self.X = AsynchronousXopt(evaluator = evaluator, generator = generator, vocs = vocs)
                    self.X.strict = False
                    # self.X = Xopt(evaluator = evaluator, generator = generator, vocs = vocs)

                    # Make an initial sample to allow XOpt to function
                    self.X.random_evaluate(initialSamples)
                    print('Finished generating initial samples')
                    
                    def Wait():
                        if len(self.X.data) == 0:
                            QTimer.singleShot(self.timeBetweenPolls, Wait)
                        else:
                            for step in range(steps):
                                self.X.step()

                            print('Optimisation finished - here is the output:')
                            print(self.X.data)
                            self.X.data.to_csv(f'{shared.cwd}\\GP-run.txt', sep = ' ', index = True, header = True)
                    Wait()
            WaitUntilInputsRead()

    def SwitchMode(self):
        if self.online:
            self.modeTitle.setText('Mode: <u><span style = "color: #C74343">Offline</span></u>')
        else:
            self.modeTitle.setText('Mode: <u><span style = "color: #3C9C29">Online</span></u>')
        self.online = not self.online

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
            self.contextSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.objectiveSocketTitle.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontSize = 16, fontColor = '#c4c4c4', borderRadiusTopLeft = 12, borderRadiusBottomLeft = 12))
            self.header.setStyleSheet(style.WidgetStyle(color = "#B54428", borderRadiusTopLeft = 8, borderRadiusTopRight = 8))
            self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 18, fontColor = '#c4c4c4'))

    def SelectedStyling(self):
        pass