from PySide6.QtWidgets import QScrollArea, QWidget, QPushButton, QLineEdit, QComboBox, QLabel, QSizePolicy, QHBoxLayout, QVBoxLayout, QSpacerItem
from PySide6.QtCore import Qt
import numpy as np
import aioca
import asyncio
import operator
from functools import reduce
import time
from datetime import datetime
from xopt import Xopt, VOCS, Evaluator
from xopt.generators.bayesian import UpperConfidenceBoundGenerator, ExpectedImprovementGenerator
# rename gpytorch kernels to avoid conflict with pipelines objects
from xopt.generators.bayesian.models.standard import StandardModelConstructor
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Queue
from multiprocessing.shared_memory import SharedMemory
from threading import Thread, Event, Lock
from ...simulator import Simulator
from ... import shared
from ..draggable import Draggable
from ...ui.runningcircle import RunningCircle
from ...actions.offline.singletaskgp import SingleTaskGPAction as OfflineAction
from ...actions.online.singletaskgp import SingleTaskGPAction as OnlineAction
from ...utils import cothread
# PerformAction is invoked when running tasks in offline mode to keep the UI responsive.
from ...utils.multiprocessing import SetGlobalToggleState, TogglePause, StopAction, CreatePersistentWorker, runningActions
from ..filters.filter import Filter
from ..pv import PV
from ..progress import Progress
from ... import style
from ... import shared

class SingleTaskGP(Draggable):
    def __init__(self, parent, proxy, **kwargs):
        # sim numerical precision set to fp32 by default to allow much higher particle populations.
        simPrecision = kwargs.pop('simPrecision', None)
        if simPrecision is None or simPrecision == 'fp32':
            simPrecision = 'fp32'
        elif simPrecision == 'fp64':
            simPrecision = 'fp64'

        super().__init__(
            proxy, name = kwargs.pop('name', 'Single Task GP'), type = 'Single Task GP', size = kwargs.pop('size', [600, 615]), 
            components = {
                'value': dict(name = 'Value', value = 0, min = 0, max = 100, default = 0, units = '', valueType = float),
            },
            acqFunction = kwargs.pop('acqFunction', 'UCB'),
            acqHyperparameter = kwargs.pop('acqHyperparameter', 2),
            numSamples = kwargs.pop('numSamples', 5),
            numSteps = kwargs.pop('numSteps', 20),
            mode = kwargs.pop('mode', 'MAXIMISE'),
            numParticles = kwargs.pop('numParticles', 10000),
            simPrecision = simPrecision,
            headerColor = "#C1492B",
            **kwargs
        )
        self.timeBetweenPolls = 1000
        self.runningCircle = RunningCircle()
        self.offlineAction = OfflineAction(self)
        self.onlineAction = OnlineAction(self)
        self.online = False
        self.isReset = False
        self.actionFinished = Event()
        self.resetApplied = Event()
        self.lock = Lock()

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
        self.activeDims = dict() # matches each PV ID to its corresponding dimension inside the optimiser (necessary when constructing composite kernels)

        self.Push()
        self.ToggleStyling(active = False)

    def __getstate__(self):
        return {
            'lattice': shared.lattice,
            'decisions': [
                {
                    'name': d.settings['linkedElement'].Name,
                    'index': d.settings['linkedElement'].Index,
                    's': d.settings['linkedElement']['s (m)'],
                    'set': d.settings['components']['value']['value'],
                }
                for d in self.decisions
            ],
            'objectives': [
                {
                    'name': o.settings['linkedElement'].Name,
                    'index': o.settings['linkedElement'].Index,
                    's': o.settings['linkedElement']['s (m)'],
                    'dtype': o.settings['dtype'],
                }
                for o in self.fundamentalObjectives
            ],
            'numParticles': self.numParticles,
            'totalSteps': self.settings['numSamples'] + self.settings['numSteps']
        }

    def __setstate__(self, state):
        self.lattice = state['lattice']
        self.simulator = Simulator(lattice = self.lattice)
        self.decisions:list = state['decisions']
        self.objectives:list = state['objectives']
        self.numObjectives:int = len(state['objectives'])
        self.sharedMemoryCreated = False
        self.numParticles = state['numParticles']
        self.totalSteps = state['totalSteps']
        self.computations = {
            'CHARGE': self.GetCharge,
            'X': self.GetX,
            'Y': self.GetY,
            'XP': self.GetXP,
            'YP': self.GetYP,
            'SURVIVAL_RATE': self.GetSurvivalRate,
        }

    def Push(self):
        from ..kernels.periodic import PeriodicKernel
        from ..composition.composition import Composition
        from ..kernels.kernel import Kernel
        super().Push()
        self.widget.layout().setContentsMargins(5, 10, 20, 10)
        self.widget.layout().setSpacing(20)
        self.AddSocket('decision', 'F', 'Decision', 175, acceptableTypes = [PV])
        self.AddSocket('objective', 'F', 'Objective', 185, acceptableTypes = [PV, Composition, Filter])
        self.AddSocket('kernel', 'F', 'Kernel', 175, acceptableTypes = [Kernel, Composition, Filter])
        self.AddSocket('out', 'M')
        self.content = QWidget()
        self.content.setLayout(QVBoxLayout())
        self.content.layout().setContentsMargins(0, 0, 0, 0)
        self.content.layout().setSpacing(25)
        self.widget.layout().addWidget(self.content)
        # settings section
        settings = QWidget()
        settings.setFixedHeight(200)
        settings.setLayout(QVBoxLayout())
        settings.layout().setContentsMargins(0, 5, 5, 0)
        settingsLabel = QLabel('<b>SETTINGS</b>')
        settingsLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 13))
        settings.layout().addWidget(settingsLabel, alignment = Qt.AlignLeft)
        # acquisition
        acquisition = QWidget()
        acquisition.setFixedHeight(30)
        acquisition.setLayout(QHBoxLayout())
        acquisition.layout().setContentsMargins(5, 0, 0, 0)
        acquisitionLabel = QLabel('Acquisition Function')
        acquisitionLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        acquisitionLabel.setAlignment(Qt.AlignLeft)
        acquisition.layout().addWidget(acquisitionLabel, alignment = Qt.AlignLeft | Qt.AlignVCenter)
        acquisitionSelect = QComboBox()
        acquisitionSelect.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        acquisitionSelect.setStyleSheet(style.ComboStyle(color = '#1e1e1e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 12))
        acquisitionSelect.view().parentWidget().setStyleSheet('color: transparent;')
        funcs = {
            '   UCB': self.SelectUCB,
            '   EI': self.SelectEI,
        }
        acquisitionSelect.addItems(funcs.keys())
        idx = 0 if self.settings['acqFunction'] == 'UCB' else 1
        acquisitionSelect.setCurrentIndex(idx)
        acquisitionSelect.currentTextChanged.connect(lambda: funcs[acquisitionSelect.currentText()]())
        acquisition.layout().addWidget(acquisitionSelect)
        settings.layout().addWidget(acquisition)
        # exploration parameter
        self.exploration = QWidget()
        self.exploration.setFixedHeight(30)
        self.exploration.setLayout(QHBoxLayout())
        self.exploration.layout().setContentsMargins(5, 0, 0, 0)
        explorationLabel = QLabel('Trade-off Parameter')
        explorationLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        explorationLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.exploration.layout().addWidget(explorationLabel)
        self.explorationEdit = QLineEdit()
        if self.settings['acqFunction'] == 'EI':
            self.explorationEdit.setReadOnly(True)
            self.explorationEdit.setText('N/A')
        else:
            self.explorationEdit.setText(f'{self.settings['acqHyperparameter']:.1f}')
        self.explorationEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.explorationEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, borderRadius = 6, paddingLeft = 13))
        self.explorationEdit.returnPressed.connect(self.ChangeAcqHyperparameter)
        self.exploration.layout().addWidget(self.explorationEdit)
        settings.layout().addWidget(self.exploration)
        # random samples
        self.samples = QWidget()
        self.samples.setFixedHeight(30)
        self.samples.setLayout(QHBoxLayout())
        self.samples.layout().setContentsMargins(5, 0, 0, 0)
        samplesLabel = QLabel('Random Samples')
        samplesLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        samplesLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.samples.layout().addWidget(samplesLabel)
        self.samplesEdit = QLineEdit(f'{self.settings['numSamples']}')
        self.samplesEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, borderRadius = 6, paddingLeft = 13))
        self.samplesEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.samplesEdit.returnPressed.connect(self.ChangeSamples)
        self.samples.layout().addWidget(self.samplesEdit)
        settings.layout().addWidget(self.samples)
        # steps
        self.steps = QWidget()
        self.steps.setFixedHeight(30)
        self.steps.setLayout(QHBoxLayout())
        self.steps.layout().setContentsMargins(5, 0, 0, 0)
        stepsLabel = QLabel('Steps')
        stepsLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        self.steps.layout().addWidget(stepsLabel)
        self.stepsEdit = QLineEdit(f'{self.settings['numSteps']}')
        self.stepsEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, borderRadius = 6, paddingLeft = 13))
        self.stepsEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.stepsEdit.returnPressed.connect(self.ChangeSteps)
        self.steps.layout().addWidget(self.stepsEdit)
        settings.layout().addWidget(self.steps)
        # mode
        self.modeWidget = QWidget()
        self.modeWidget.setFixedHeight(30)
        self.modeWidget.setLayout(QHBoxLayout())
        self.modeWidget.layout().setContentsMargins(5, 0, 0, 0)
        self.modeLabel = QLabel(f'Mode:\t{self.settings['mode'].upper()}')
        self.modeLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        self.modeWidget.layout().addWidget(self.modeLabel)
        self.modeButton = QPushButton('Switch')
        self.modeButton.setStyleSheet(style.PushButtonBorderlessStyle(color = '#3e3e3e', hoverColor = '#3c3c3c', fontColor = '#c4c4c4', fontSize = 12, borderRadius = 6))
        self.modeButton.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.modeButton.pressed.connect(self.ChangeMode)
        self.modeWidget.layout().addWidget(self.modeButton)
        settings.layout().addWidget(self.modeWidget)
        # spacer
        settings.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.content.layout().addWidget(settings)
        # metrics section
        metrics = QWidget()
        metrics.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        metrics.setLayout(QVBoxLayout())
        metrics.layout().setContentsMargins(0, 5, 5, 0)
        metricsLabel = QLabel('<b>METRICS</b>')
        metricsLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 13))
        metrics.layout().addWidget(metricsLabel, alignment = Qt.AlignLeft)
        # time start
        timeStart = QWidget()
        timeStart.setFixedHeight(30)
        timeStart.setLayout(QHBoxLayout())
        timeStart.layout().setContentsMargins(5, 0, 0, 0)
        timeStartLabel = QLabel(f'Time at Start (H/M/S)')
        timeStartLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        timeStart.layout().addWidget(timeStartLabel)
        self.timestamp = QLineEdit(f'N/A')
        self.timestamp.setReadOnly(True)
        self.timestamp.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, paddingLeft = 13, borderRadius = 6))
        self.timestamp.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        timeStart.layout().addWidget(self.timestamp)
        metrics.layout().addWidget(timeStart)
        # run time
        runTime = QWidget()
        runTime.setFixedHeight(30)
        runTime.setLayout(QHBoxLayout())
        runTime.layout().setContentsMargins(5, 0, 0, 0)
        runTimeLabel = QLabel('Run Time (s)')
        runTimeLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        runTime.layout().addWidget(runTimeLabel)
        self.runTimeEdit = QLineEdit('N/A')
        self.runTimeEdit.setReadOnly(True)
        self.runTimeEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, paddingLeft = 13, borderRadius = 6))
        self.runTimeEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        runTime.layout().addWidget(self.runTimeEdit)
        metrics.layout().addWidget(runTime)
        # progress
        progress = QWidget()
        progress.setFixedHeight(30)
        progress.setLayout(QHBoxLayout())
        progress.layout().setContentsMargins(5, 0, 0, 0)
        progressLabel = QLabel('Progress (%)')
        progressLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        progress.layout().addWidget(progressLabel)
        self.progressEdit = QLineEdit('N/A')
        self.progressEdit.setReadOnly(True)
        self.progressEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, paddingLeft = 13, borderRadius = 6))
        self.progressEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        progress.layout().addWidget(self.progressEdit)
        metrics.layout().addWidget(progress)
        # best
        best = QWidget()
        best.setFixedHeight(30)
        best.setLayout(QHBoxLayout())
        best.layout().setContentsMargins(5, 0, 0, 0)
        bestLabel = QLabel('Best Result')
        bestLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        best.layout().addWidget(bestLabel)
        self.bestEdit = QLineEdit('N/A')
        self.bestEdit.setReadOnly(True)
        self.bestEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, paddingLeft = 13, borderRadius = 6))
        self.bestEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        best.layout().addWidget(self.bestEdit)
        metrics.layout().addWidget(best)
        # candidate
        candidate = QWidget()
        candidate.setFixedHeight(30)
        candidate.setLayout(QHBoxLayout())
        candidate.layout().setContentsMargins(5, 0, 0, 0)
        candidateLabel = QLabel('Best Candidate')
        candidateLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        candidate.layout().addWidget(candidateLabel)
        self.candidateEdit = QLineEdit('N/A')
        self.candidateEdit.setReadOnly(True)
        self.candidateEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, paddingLeft = 13, borderRadius = 6))
        self.candidateEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        candidate.layout().addWidget(self.candidateEdit)
        metrics.layout().addWidget(candidate)
        # average
        average = QWidget()
        average.setFixedHeight(30)
        average.setLayout(QHBoxLayout())
        average.layout().setContentsMargins(5, 0, 0, 0)
        averageLabel = QLabel('Moving Average')
        averageLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        average.layout().addWidget(averageLabel)
        self.averageEdit = QLineEdit('N/A')
        self.averageEdit.setReadOnly(True)
        self.averageEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, paddingLeft = 13, borderRadius = 6))
        self.averageEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        average.layout().addWidget(self.averageEdit)
        metrics.layout().addWidget(average)
        self.content.layout().addWidget(metrics)
        # progress bar
        progressWidget = QWidget()
        progressWidget.setLayout(QVBoxLayout())
        progressWidget.layout().setContentsMargins(15, 0, 0, 0)
        self.progressBar = Progress(self)
        progressWidget.layout().addWidget(self.progressBar)
        self.widget.layout().addWidget(progressWidget)
        self.BaseStyling()

    def UpdateMetrics(self):
        while True:
            if self.ID in runningActions:
                tm = time.time()
                if not runningActions[self.ID][0].is_set():
                    self.runTimeAmount += tm - self.t0
                    self.runTimeEdit.setText(f'{self.runTimeAmount:.0f}')
                if self.actionFinished.is_set():
                    break
                self.t0 = tm
            else:
                break
            time.sleep(.2)

    def Timestamp(self):
        return datetime.now().strftime('%H:%M:%S')

    def ChangeMode(self):
        self.settings['mode'] = 'MAXIMISE' if self.settings['mode'] == 'MINIMISE' else 'MINIMISE'
        self.modeLabel.setText(f'Mode:\t{self.settings['mode']}')
        shared.workspace.assistant.PushMessage(f'Successfully changed mode of {self.name} to {self.settings['mode']}.')

    def ChangeAcqHyperparameter(self):
        try:
            val = float(self.explorationEdit.text())
        except:
            shared.workspace.assistant.PushMessage(f'Failed to change the acquisition function exploration hyperparameter of {self.name} because it isn\'t an int or float.', 'Error')
            return
        idx = self.exploration.layout().indexOf(self.explorationEdit)
        self.exploration.layout().removeWidget(self.explorationEdit)
        self.explorationEdit.deleteLater()
        newText = f'{val:.1f}'
        newExplorationEdit = QLineEdit(newText)
        newExplorationEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, borderRadius = 6, paddingLeft = 13))
        newExplorationEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        newExplorationEdit.returnPressed.connect(self.ChangeAcqHyperparameter)
        self.exploration.layout().insertWidget(idx, newExplorationEdit)
        self.explorationEdit = newExplorationEdit
        self.settings['acqHyperparameter'] = float(newText)
        shared.workspace.assistant.PushMessage(f'Successfully changed the acquisition function exploration hyperparameter of {self.name} to {newText}.')

    def ChangeSamples(self):
        try:
            val = round(float(self.samplesEdit.text()))
        except:
            shared.workspace.assistant.PushMessage(f'Failed to change the number of initial random samples of {self.name} because it isn\'t an int or float.', 'Error')
            return
        idx = self.samples.layout().indexOf(self.samplesEdit)
        self.samples.layout().removeWidget(self.samplesEdit)
        self.samplesEdit.deleteLater()
        newText = f'{val}'
        newSamplesEdit = QLineEdit(newText)
        newSamplesEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, borderRadius = 6, paddingLeft = 13))
        newSamplesEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        newSamplesEdit.returnPressed.connect(self.ChangeSamples)
        self.samples.layout().insertWidget(idx, newSamplesEdit)
        self.samplesEdit = newSamplesEdit
        self.settings['numSamples'] = val
        shared.workspace.assistant.PushMessage(f'Successfully changed the number of initial random samples of {self.name} to {newText}.')

    def ChangeSteps(self):
        try:
            val = round(float(self.stepsEdit.text()))
        except:
            shared.workspace.assistant.PushMessage(f'Failed to change the number of steps of {self.name} because it isn\'t an int or float.', 'Error')
            return
        idx = self.steps.layout().indexOf(self.stepsEdit)
        self.steps.layout().removeWidget(self.stepsEdit)
        self.stepsEdit.deleteLater()
        newText = f'{val}'
        newStepsEdit = QLineEdit(newText)
        newStepsEdit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, borderRadius = 6, paddingLeft = 13))
        newStepsEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        newStepsEdit.returnPressed.connect(self.ChangeSteps)
        self.steps.layout().insertWidget(idx, newStepsEdit)
        self.stepsEdit = newStepsEdit
        self.settings['numSteps'] = val
        shared.workspace.assistant.PushMessage(f'Successfully changed the maximum number of steps of {self.name} to {newText}.')

    def SelectUCB(self):
        self.settings['acqFunction'] = 'UCB'
        self.explorationEdit.setText(f'{self.settings['acqHyperparameter']:.1f}')
        self.explorationEdit.setReadOnly(False)
        shared.workspace.assistant.PushMessage(f'Successfully changed the acquisition function of {self.name} to UCB (Upper Confidence Bound).')

    def SelectEI(self):
        self.settings['acqFunction'] = 'EI'
        self.explorationEdit.setText('N/A')
        self.explorationEdit.setReadOnly(True)
        shared.workspace.assistant.PushMessage(f'Successfully changed the acquisition function of {self.name} to EI (Expected Improvement).')

    def ConstructKernel(self):
        '''Traces the kernel structure up the pipeline and returns an Xopt compatible composition.'''
        # fetch the block attached to the kernel socket
        kernel = [ID for ID, link in self.linksIn.items() if link['socket'] == 'kernel'][0] # assume a single match for now ... (will be replaced)
        return self.GetKernelStructure(kernel)

    def GetKernelStructureString(self, ID):
        '''Will need to be extended in the future.'''
        from ..composition.add import Add
        entity = shared.entities[ID]
        if len(entity.linksIn) > 0:
            # assume this is a composition for now ...
            if isinstance(entity, Add):
                return [self.GetKernelStructure(ID) for ID in entity.linksIn]
            return tuple(self.GetKernelStructure(ID) for ID in entity.linksIn)
        return entity.__class__
    
    def GetKernelStructure(self, ID):
        '''Will need to be extended in the future.'''
        from gpytorch.kernels import RBFKernel as _RBFKernel, PeriodicKernel as _PeriodicKernel, ScaleKernel
        from ..kernels.rbf import RBFKernel
        from ..kernels.periodic import PeriodicKernel
        from ..composition.add import Add
        entity = shared.entities[ID]
        if len(entity.linksIn) > 0:
            # assume this is a composition for now ...
            if isinstance(entity, Add):
                result = reduce(operator.add, [self.GetKernelStructure(ID) for ID in entity.linksIn])
                return result
            return reduce(operator.mul, [self.GetKernelStructure(ID) for ID in entity.linksIn])
        # return a GPytorch kernel object
        if isinstance(entity, RBFKernel):
            if entity.settings['automatic']:
                return ScaleKernel(_RBFKernel())
            return ScaleKernel(_RBFKernel(active_dims = sorted([self.activeDims[linkedPVID] for linkedPVID in entity.settings['linkedPVs']])))
        elif isinstance(entity, PeriodicKernel):
            if entity.settings['automatic']:
                return ScaleKernel(_PeriodicKernel())
            return ScaleKernel(_PeriodicKernel(active_dims = sorted([self.activeDims[linkedPVID] for linkedPVID in entity.settings['linkedPVs']])))

    def GetObjectiveIDs(self, ID, objectives = set([]), socketNameFilter = None):
        entity = shared.entities[ID]
        linksIn = [linkID for linkID, v in entity.linksIn.items() if v['socket'] == socketNameFilter] if socketNameFilter is not None else [linkID for linkID, v in entity.linksIn.items()]
        if len(linksIn) > 0:
            for linkID in linksIn:
                objectives = objectives.union(self.GetObjectiveIDs(linkID, objectives)) # union set with newly found objectives
            return list(objectives)
        if isinstance(entity, PV):
            return set([ID])
        return set([])

    def CheckDecisionStatesAgree(self):
        for d in self.decisions:
            if d.online != self.decisions[0].online:
                shared.workspace.assistant.PushMessage(f'All decision variables of {self.name} must share the same Online or Offline state.', 'Error')
                return False
            if d.online and np.isinf(d.data[1]):
                shared.workspace.assistant.PushMessage(f'{d.name} is not supplying a live value to {self.name}.', 'Error')
                return False
        return True

    def SetupAndRunOptimiser(self, evaluateFunction):
        shared.workspace.assistant.PushMessage(f'{self.name} is setting up for the first time, which may take a few seconds.')
        mode = 'MAXIMIZE' if self.settings['mode'].upper() == 'MAXIMISE' else 'MINIMIZE'
        variables = dict()
        self.immediateObjectiveName = f'{self.objectives[0].name} (ID: {self.objectives[0].ID})'
        for _, d in enumerate(self.decisions):
            self.activeDims[d.ID] = _
            variables[f'{d.name} (ID: {d.ID})'] = [d.settings['components']['value']['min'], d.settings['components']['value']['max']]
        vocs = VOCS(
            variables = variables,
            objectives = {
                self.immediateObjectiveName: mode,
            },
        )
        kernel = self.ConstructKernel()
        constructor = StandardModelConstructor(
            covar_modules = {
                self.immediateObjectiveName: kernel,
            },
        )
        if self.settings['acqFunction'] == 'UCB':
            generator = UpperConfidenceBoundGenerator(
                vocs = vocs,
                gp_constructor = constructor,
                beta = self.settings['acqHyperparameter'],
            )
        else:
            generator = ExpectedImprovementGenerator(
                vocs = vocs,
                gp_constructor = constructor,
            )

        evaluator = Evaluator(function = evaluateFunction)
        self.X = Xopt(
            vocs = vocs,
            generator = generator,
            evaluator = evaluator,
        )
        self.bestValue = None
        self.bestCandidate = None
        self.runningAverageWindow = 5
        self.lastValues = np.array([])
        self.initialised = False
        self.X.random_evaluate(1) # run once to initialise shared memory array
        self.initialised = True
        self.X.data.drop(0, inplace = True)
        self.numEvals = 0
        shared.workspace.assistant.PushMessage(f'{self.name} is now running.')
        self.X.random_evaluate(np.maximum(self.settings['numSamples'], 1))
        if self.settings['numSteps'] > 0:
            for it in range(self.settings['numSteps']):
                self.X.step()
                self.X.generator.train_model()
                # allow user to break out of this for loop.
                if self.stopCheckThread.is_set():
                    self.stopCheckThread.clear()
                    break
        self.inQueue.put(None)
        # set the STOP flag to allow the runningAction to be cleaned up.
        if self.ID in runningActions:
            runningActions[self.ID][1].set()
        if not self.isReset:
            self.progressAmount = 1
            self.progressEdit.setText('100')
            self.progressBar.CheckProgress(self.progressAmount)

    def Pause(self, changeGlobalToggleState = True):
        with self.lock:
            if not self.actionFinished.is_set():
                if self.ID in runningActions and not runningActions[self.ID][0].is_set():
                    TogglePause(self, changeGlobalToggleState)
                    if runningActions[self.ID][0].is_set():
                        self.progressBar.TogglePause(True)
                    else:
                        self.progressBar.TogglePause(False)

    def Stop(self):
        StopAction(self)

    def Reset(self):
        self.stopCheckThread.set()
        self.isReset = True
        super().Reset()
        self.progressBar.Reset()

    def Start(self, changeGlobalToggleState = True, **kwargs):
        if self.ID in runningActions:
            if runningActions[self.ID][0].is_set():
                TogglePause(self, changeGlobalToggleState)
                self.progressBar.TogglePause(False)
            return
        
        self.isReset = False
        self.actionFinished.clear()
        self.progressBar.Reset()
        self.decisions = []
        for ID, v in self.linksIn.items():
            if v['socket'] == 'decision':
                self.decisions.append(shared.entities[ID])
        # objective leaf nodes that determine the final objective value witnessed by the block.
        self.fundamentalObjectives = [shared.entities[ID] for ID in self.GetObjectiveIDs(self.ID, socketNameFilter = 'objective')]
        # objectives with immediate connections to this block.
        self.objectives = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'objective']
        immediateObjectiveName = f'{self.objectives[0].name} (ID: {self.objectives[0].ID})'

        if not self.CheckDecisionStatesAgree():
            return
        self.online = self.decisions[0].online
        self.numParticles = 10000
        self.numEvals = 0
        self.maxEvals = self.settings['numSamples'] + self.settings['numSteps']
        self.t0 = time.time()
        self.runTimeAmount = 0
        self.progressAmount = 0

        precision = np.float32 if self.settings['simPrecision'] == 'fp32' else np.float64
        emptyArray = np.empty(len(self.fundamentalObjectives), dtype = precision)
        self.inQueue, self.outQueue = Queue(), Queue()

        if not self.online:
            CreatePersistentWorker(self, emptyArray, self.inQueue, self.outQueue, self.Simulate, 0.)
        SetGlobalToggleState()

        def Evaluate(dictIn: dict):
            if self.ID not in runningActions or runningActions[self.ID][1].is_set():
                return {immediateObjectiveName: np.nan}
            self.progressAmount = self.numEvals / self.maxEvals
            self.progressEdit.setText(f'{self.progressAmount * 1e2:.0f}')
            self.progressBar.CheckProgress(self.progressAmount)
            self.numEvals += 1
            self.inQueue.put([dictIn])
            simResult = self.outQueue.get()
            # a reset interrupt can cause this to set simResult to None -- handle this
            if self.ID not in runningActions or runningActions[self.ID][1].is_set():
                return {immediateObjectiveName: np.nan}
            # trying to change pv values from a separate process will not work.
            for it, o in enumerate(self.fundamentalObjectives):
                o.data[1] = simResult[it]
            t = Thread(target = self.objectives[0].Start)
            t.start()
            t.join()
            if self.initialised:
                if self.lastValues.shape[0] > self.runningAverageWindow:
                    self.lastValues = np.delete(self.lastValues, 0)
                self.lastValues = np.append(self.lastValues, np.array([self.objectives[0].data[1]]))
                self.averageEdit.setText(f'{np.nanmean(self.lastValues):.3f}')
                if self.settings['mode'].upper() == 'MAXIMISE':
                    if self.bestValue is None or self.bestValue < self.objectives[0].data[1]:
                        self.bestValue = self.objectives[0].data[1]
                        self.bestEdit.setText(f'{self.bestValue:.3f}')
                        self.bestCandidate = np.array(list(dictIn.values()))
                        s = ''
                        for d in dictIn.values():
                            s += f'{d:.3f}  '
                        self.candidateEdit.setText(s)
                elif self.settings['mode'].upper() == 'MINIMISE':
                    if self.bestValue is None or self.bestValue > self.objectives[0].data[1]:
                        self.bestValue = self.objectives[0].data[1]
                        self.bestEdit.setText(f'{self.bestValue:.3f}')
                        self.bestCandidate = np.array(list(dictIn.values()))
                        s = ''
                        for d in dictIn.values():
                            s += f'{d:.3f}  '
                        self.candidateEdit.setText(s)
            
            return {immediateObjectiveName: self.objectives[0].data[1]}

        self.timestamp.setText(self.Timestamp())
        self.progressEdit.setText('0')
        self.bestEdit.setText('N/A')
        self.candidateEdit.setText('N/A')
        self.averageEdit.setText('N/A')
        Thread(target = self.SetupAndRunOptimiser, args = (Evaluate,), daemon = True).start()
        Thread(target = self.UpdateMetrics, daemon = True).start()

    def Simulate(self, pause, stop, error, progress, sharedMemoryName, shape, dtype, parameters, **kwargs):
        '''Action does this:
            1. Track Beam
            2. Store objectives vector in data
            3. Return
        '''
        numRepeats = 5
        self.simulator.numParticles = self.numParticles
        
        if not self.sharedMemoryCreated:
            self.sharedMemory = SharedMemory(name = sharedMemoryName)
            self.sharedMemoryCreated = True
        data = np.ndarray(shape, dtype, buffer = self.sharedMemory.buf)
        result = np.zeros((numRepeats, self.numObjectives))

        for d in parameters:
            idx = int(d.split('Index: ')[1].split(')')[0])
            # convert steerer values to mrad.
            if 'HSTR' in d:
                self.lattice[idx].KickAngle[0] = parameters[d] * 1e-3
            elif 'VSTR' in d:
                self.lattice[idx].KickAngle[1] = parameters[d] * 1e-3

        for r in range(numRepeats):
            tracking, _ = self.simulator.TrackBeam(self.numParticles)
            for it, o in enumerate(self.objectives):
                result[r, it] = self.computations[o['dtype']](tracking, o['index'])
                # check for interrupts
                while pause.is_set():
                    if stop.is_set():
                        self.sharedMemory.close()
                        self.sharedMemory.unlink()
                        return
                    time.sleep(.1)
                if stop.is_set():
                    self.sharedMemory.close()
                    self.sharedMemory.unlink()
                    return
        np.copyto(data, np.mean(result, axis = 0))
        return data

    def GetCharge(self, tracking, index):
        '''Returns charge at an element in units of fundamental charge, q.'''
        return np.sum(np.where(np.any(np.isnan(tracking[:, :, index, 0]), axis = 0), False, True))

    def GetX(self, tracking, index):
        '''Returns the centroid of the beam in the horizontal axis at an element.'''
        return np.nanmean(tracking[0, :, index, 0])

    def GetY(self, tracking, index):
        '''Returns the centroid of the beam in the vertical axis at an element.'''
        return np.nanmean(tracking[2, :, index, 0])

    def GetXP(self, tracking, index):
        '''Returns the horizontal momentum of the beam at an element.'''
        return np.nanmean(tracking[1, :, index, 0])

    def GetYP(self, tracking, index):
        '''Returns the vertical momentum of the beam at an element.'''
        return np.nanmean(tracking[3, :, index, 0])
    
    def GetSurvivalRate(self, tracking, index):
        return np.sum(np.where(np.any(np.isnan(tracking[:, :, index, 0]), axis = 0), False, True)) / self.numParticles

    # will be removed soon ...
    async def _Start(self, **kwargs):
        # Prevents GP from spooling up another job if one is already running but paused.
        if self.ID in runningActions:
            if runningActions[self.ID][0].is_set():
                TogglePause(self)
            return
        
        # self.decisions = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'decision']
        # self.objectives = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'objective']
        # this will be deprecated soon
        # independents = [
        #     {'ID': d.ID, 'stream': self.streamTypesIn[d.ID]} for d in self.decisions
        # ]
        # waiting = False
        # force it online for now ...
        # self.online = True
        # actionToRun.decisions = self.decisions
        # actionToRun.objectives = self.objectives
        # for decision in self.decisions:
        #     if decision.type not in self.pvBlockTypes and np.isinf(decision.streams[self.streamTypesIn[decision.ID]]()['data']).any():
        #         waiting = True
        #         self.title.setText(f'{self.title.text().split(' (')[0]} (Waiting)')
        #         await actionToRun.ReadDependents(independents)
        #         break
        self.decisions = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'decision']
        self.objectives = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'objective']
        self.online = self.decisions[0].online
        # Check states of decision variables. All must share the same online / offline state. If online, check they are streaming values.
        for decision in self.decisions:
            if decision.online != self.decisions[0].online:
                shared.workspace.assistant.PushMessage(f'All decision variables of {self.name} must share the same Online or Offline state.', 'Error')
                return
            if decision.online:
                if np.isinf(decision.data[1]):
                    shared.workspace.assistant.PushMessage(f'{decision.name} is not supplying a live value to {self.name}.', 'Error')
                    return
        self.timestamp.setText(self.Timestamp())
        self.progress = 0
        self.total = self.settings['numSamples'] + self.settings['numSteps']
        self.t0 = time.time()

        async def WaitUntilInputsRead():
            mode = 'MAXIMIZE' if self.settings['mode'] == 'maximise' else 'MINIMIZE'
            variables = dict()
            for _, d in enumerate(self.decisions):
                self.activeDims[d.ID] = _
                variables[f'{d.name} (ID: {d.ID})'] = [d.settings['components']['value']['min'], d.settings['components']['value']['max']]
            vocs = VOCS(
                variables = variables,
                objectives = {
                    f'{self.objectives[0].name} (ID: {self.objectives[0].ID})': mode,
                },
            )
            kernel = self.ConstructKernel()
            constructor = StandardModelConstructor(
                covar_modules = {
                    f'{self.objectives[0].name} (ID: {self.objectives[0].ID})': kernel,
                },
            )
            if self.settings['acqFunction'] == 'UCB':
                generator = UpperConfidenceBoundGenerator(
                    vocs = vocs,
                    gp_constructor = constructor,
                    beta = self.settings['acqHyperparameter'],
                )
            else:
                generator = ExpectedImprovementGenerator(
                    vocs = vocs,
                    gp_constructor = constructor,
                )

            if self.online:
                await self.OnlineOptimisation(vocs, generator)
            else:
                print('Offline Optimisation for the win!')
                await self.OfflineOptimisation(vocs, generator)
            # async def SetDecisionsAndRecordResponse(dictIn: dict):
            #     try:
            #         for d in self.decisions:
            #             dictName = f'{d.name} + (ID: {d.ID})'
            #             if dictIn[dictName] < await aioca.caget(d.name + ':I'):
            #                 await aioca.caput(d.name + ':SETI', dictIn[dictName] - .2)
            #         await aioca.sleep(2)
            #         await aioca.caput(d.name + ':SETI', dictIn[dictName])
            #         await aioca.sleep(1)

            #         result = await self.objectives[0].Start()
            #     except:
            #         result = -1
            #     return {f'{self.objectives[0].name} (ID: {self.objectives[0].ID})': result}
            # self.progress = 0
            # self.total = self.settings['numSamples'] + self.settings['numSteps']
            # self.t0 = time.time()
            # def Evaluate(dictIn: dict):
            #     self.progress += 1
            #     self.progressEdit.setText(f'{self.progress / self.total * 100:.1f}')
            #     self.runTimeEdit.setText(f'{round(time.time() - self.t0)}')
            #     dictOut = asyncio.run(SetDecisionsAndRecordResponse(dictIn))
            #     return dictOut
            
            # evaluator = Evaluator(function = Evaluate)
            # X = Xopt(
            #     vocs = vocs,
            #     generator = generator,
            #     evaluator = evaluator,
            # )

            # try:
            #     await asyncio.wait_for(
            #         aioca.caput('LI-TI-MTGEN-01:START', 1, throw = True),
            #         timeout = 2,
            #     )
            #     self.runTimeEdit.setText(self.Timestamp())
            #     shared.workspace.assistant.PushMessage(f'Optimisation beginning and LINAC successfully activated.')
            # except Exception as e:
            #     shared.workspace.assistant.PushMessage(f'Failed to start up the LINAC due to a PV timeout.', 'Error')
            #     return
                
            # executor = ThreadPoolExecutor(max_workers = 1)
            # job = executor.submit(X.random_evaluate, self.settings['numSamples'])
            # job.result()

            # try:
            #     await asyncio.wait_for(
            #         aioca.caput('LI-TI-MTGEN-01:STOP', 1, throw = True),
            #         timeout = 2,
            #     )
            #     shared.workspace.assistant.PushMessage(f'Optimisation complete and LINAC successfully deactivated.')
            # except Exception as e:
            #     shared.workspace.assistant.PushMessage(f'Failed to stop up the LINAC due to a PV timeout. User should manually stop it now.', 'Error')
            #     return

        # RE-ENABLE THIS ...
        # async def WaitUntilInputsRead():
        #     nonlocal numParticles, waiting
        #     # RE-ENABLE THIS ...
        #     # if waiting:
        #     #     if not actionToRun.resultsWritten:
        #     #         return QTimer.singleShot(actionToRun.timeBetweenPolls, WaitUntilInputsRead)
        #     #     waiting = False
        #     #     return QTimer.singleShot(actionToRun.timeBetweenPolls, WaitUntilInputsRead)
        #     # else:
        #     #     if not await actionToRun.CheckForValidInputs():
        #     #         print('Failed to Start Optimisation (Returning ...)')
        #     #         return

        #         independentsToSet = {
        #             d.ID: d.streams[self.streamTypesIn[d.ID]]() for d in self.decisions
        #         }
                
        #         counter = 0
                    
        #         # def PerformActionAndWait(inDict: dict):
        #         #     '''Called on a separate worker thread so will not block the UI thread.'''
        #         #     nonlocal counter, actionToRun
        #         #     # Set the values of the decisions
        #         #     actionToRun.SetIndependents(independentsToSet, inDict)
        #         #     # crank the handle
        #         #     PerformAction(
        #         #         self,
        #         #         # Raw data held by the GP block will be output from tracking simulations
        #         #         np.empty((6, numParticles, len(shared.lattice), 1)),
        #         #         numSteps = steps,
        #         #         currentStep = counter,
        #         #         numParticles = numParticles,
        #         #     )
        #         #     while np.isnan(self.data).any():
        #         #         time.sleep(self.timeBetweenPolls / 1e3)

        #         #     counter += 1
        #         #     # Read the value of the objective by feeding this GP's data upstream
        #         #     actionToRun.ReadDependents([{'ID': self.objectives[0].ID, 'stream': self.streamTypesIn[self.objectives[0].ID]}], self.data)

        #         #     while not actionToRun.resultsWritten:
        #         #         time.sleep(self.timeBetweenPolls / 1e3)

        #         #     return {'f': self.objectives[0].streams[self.streamTypesIn[self.objectives[0].ID]]()['data']}
                    
        #         variables = dict()
        #         # for d in self.decisions:
        #         #     stream = d.streams[self.streamTypesIn[d.ID]]()
        #         #     for dim in range(stream['data'].shape[0]): # each row is a new singular vector for SVD, otherwise a 1x1 for a PV.
        #         #         variables[f'{d.ID}-{dim}'] = [-3, 3] # values get sent through tanh so restrict to sensible domain
        #         for d in self.decisions:
        #             variables[f'{d.name} (ID: {d.ID})'] = [d.settings['components']['value']['min'], d.settings['components']['value']['max']]
        #         vocs = VOCS(
        #             variables = variables,
        #             objectives = {'f': 'MINIMIZE'},
        #         )
        #         print('All Done!')

        #         # RE-ENABLE THIS ...
        #         # executor = ThreadPoolExecutor(max_workers = 1)

        #         # async def SetDecisionsAndRecordResponse(dictIn: dict):
        #         #     for d in self.decisions:
        #         #         if dictIn[d.name] < await aioca.caget(d.name + ':I'):
        #         #             await aioca.caput(d.name + ':SETI', dictIn[d.name] - .2)
        #         #     await aioca.sleep(2)
        #         #     await aioca.caput(d.name + ':SETI', dictIn[d.name])
        #         #     await aioca.sleep(1)

        #         #     result = await self.objectives[0].Start()
        #         #     return {'f': result}

        #         # def Evaluate(dictIn: dict):
        #         #     dictOut = asyncio.create_task(SetDecisionsAndRecordResponse(dictIn))
        #         #     return dictOut

        #         # evaluator = Evaluator(function = Evaluate)
        #         # generator = UpperConfidenceBoundGenerator(vocs = vocs)
        #         # self.X = Xopt(evaluator = evaluator, generator = generator, vocs = vocs)

        #         # totalSamples = steps + initialSamples
        #         # job = executor.submit(self.X.random_evaluate, initialSamples)

        #         # def StepUntilComplete():
        #         #     '''Steps through optimisation steps until finish criterion satisfied.'''
        #         #     if len(self.X.data) < totalSamples:
        #         #         print(f'On step {len(self.X.data) - initialSamples + 1}/{steps}')
        #         #         self.X.data.to_csv(shared.cwd + f'\\datadump\\{self.name}.csv', index = False)
        #         #         job = executor.submit(self.X.step)
        #         #         job.add_done_callback(lambda _: StepUntilComplete())
        #         #     else:
        #         #         # temporarily save the data automatically here
        #         #         print('GP data temporarily saved to:', Path(shared.cwd) / 'datadump' / f'{self.name}.csv')
        #         #         self.X.data.to_csv(Path(shared.cwd) / 'datadump' / f'{self.name}.csv', index = False)
        #         #         QTimer.singleShot(0, lambda: executor.shutdown(wait = True))

        #         # await aioca.caput('LI-TI-MTGEN-01:START', 1, timeout = 2)
        #         # print('LINAC active!')
        #         # job.add_done_callback(lambda _: StepUntilComplete())
        #         # await aioca.caput('LI-TI-MTGEN-01:STOP', 1, timeout = 2)
        #         # print('LINAC deactivated!')
        asyncio.create_task(WaitUntilInputsRead())

    # will also be removed soon ...
    async def OnlineOptimisation(self, vocs, generator):
        async def SetDecisionsAndRecordResponse(dictIn: dict):
            try:
                for d in self.decisions:
                    dictName = f'{d.name} + (ID: {d.ID})'
                    if dictIn[dictName] < await aioca.caget(d.name + ':I'):
                        await aioca.caput(d.name + ':SETI', dictIn[dictName] - .2)
                await aioca.sleep(2)
                await aioca.caput(d.name + ':SETI', dictIn[dictName])
                await aioca.sleep(1)

                result = await self.objectives[0].Start()
            except:
                result = -1
            return {f'{self.objectives[0].name} (ID: {self.objectives[0].ID})': result}

        def Evaluate(dictIn: dict):
            self.progress += 1
            self.progressEdit.setText(f'{self.progress / self.total * 100:.1f}')
            self.runTimeEdit.setText(f'{round(time.time() - self.t0)}')
            dictOut = asyncio.run(SetDecisionsAndRecordResponse(dictIn))
            return dictOut
        
        evaluator = Evaluator(function = Evaluate)
        X = Xopt(
            vocs = vocs,
            generator = generator,
            evaluator = evaluator,
        )

        try:
            await asyncio.wait_for(
                aioca.caput('LI-TI-MTGEN-01:START', 1, throw = True),
                timeout = 2,
            )
            self.runTimeEdit.setText(self.Timestamp())
            shared.workspace.assistant.PushMessage(f'Optimisation beginning and LINAC successfully activated.')
        except Exception as e:
            shared.workspace.assistant.PushMessage(f'Failed to start up the LINAC due to a PV timeout.', 'Error')
            return
            
        executor = ThreadPoolExecutor(max_workers = 1)
        job = executor.submit(X.random_evaluate, self.settings['numSamples'])
        job.result()

        try:
            await asyncio.wait_for(
                aioca.caput('LI-TI-MTGEN-01:STOP', 1, throw = True),
                timeout = 2,
            )
            shared.workspace.assistant.PushMessage(f'Optimisation complete and LINAC successfully deactivated.')
        except Exception as e:
            shared.workspace.assistant.PushMessage(f'Failed to stop up the LINAC due to a PV timeout. User should manually stop it now.', 'Error')
            return

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

    def AddLinkIn(self, ID, socket, **kwargs):
        if shared.entities[ID].type == 'SVD':
            super().AddLinkIn(ID, socket, streamTypeIn = 'evecs', **kwargs)
        else:
            super().AddLinkIn(ID, socket, **kwargs)
        
        self.CheckState()
        return True

    def BaseStyling(self):
        super().BaseStyling()
        if shared.lightModeOn:
            pass
        else:
            self.main.setStyleSheet(style.WidgetStyle(color = 'none', borderRadius = 12, fontColor = '#c4c4c4', fontSize = 16))
            self.progressBar.setStyleSheet(style.WidgetStyle(color = "#3e3e3e", borderRadius = 6))
            self.progressBar.innerWidget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 5))
            self.progressBar.bar.setStyleSheet(style.WidgetStyle(color = '#c4c4c4', borderRadius = 4))

    def SelectedStyling(self):
        pass