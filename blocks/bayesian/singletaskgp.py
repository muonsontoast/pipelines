from PySide6.QtWidgets import QWidget, QPushButton, QLineEdit, QComboBox, QLabel, QSizePolicy, QHBoxLayout, QVBoxLayout, QSpacerItem
from PySide6.QtCore import Qt, Signal
import numpy as np
import operator
from functools import reduce
import time
from datetime import datetime
from xopt import Xopt, VOCS, Evaluator
from xopt.generators.bayesian import UpperConfidenceBoundGenerator, ExpectedImprovementGenerator
from xopt.generators.bayesian.models.standard import StandardModelConstructor
from multiprocessing import Event
from multiprocessing.shared_memory import SharedMemory
from threading import Thread, Lock
from queue import Queue
from ...simulator import Simulator
from ... import shared
from ..draggable import Draggable
from ...utils import cothread
# PerformAction is invoked when running tasks in offline mode to keep the UI responsive.
from ...utils.multiprocessing import SetGlobalToggleState, TogglePause, StopAction, CreatePersistentWorker, runningActions
from ..filters.filter import Filter
from ..number import Number
from ..pv import PV
from ..progress import Progress
from ... import style
from ... import shared

class SingleTaskGP(Draggable):
    updateProgressSignal = Signal(float)
    updateRunTimeSignal = Signal(float)
    updateAverageSignal = Signal(float)
    updateBestSignal = Signal(float)
    updateCandidateSignal = Signal(str)

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
        self.online = False
        self.isReset = False
        self.actionFinished = Event()
        self.resetApplied = Event()
        self.lock = Lock()

        # connect signals to their logic
        self.updateProgressSignal.connect(self.UpdateProgressLabel)
        self.updateRunTimeSignal.connect(self.UpdateRunTimeLabel)
        self.updateAverageSignal.connect(self.UpdateAverageLabel)
        self.updateBestSignal.connect(self.UpdateBestLabel)
        self.updateCandidateSignal.connect(self.UpdateCandidateLabel)

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
        timeStartLabel = QLabel(f'Start Time')
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

    def UpdateProgressLabel(self, progress):
        self.progressEdit.setText(f'{self.progressAmount * 1e2:.0f}')
        with self.lock:
            if not self.stopCheckThread.is_set():
                self.progressBar.CheckProgress(self.progressAmount)

    def UpdateRunTimeLabel(self, runTimeAmount):
        self.runTimeEdit.setText(f'{self.runTimeAmount:.0f}')

    def UpdateAverageLabel(self, avg):
        self.averageEdit.setText(f'{avg:.3f}')

    def UpdateBestLabel(self, bestValue):
        self.bestEdit.setText(f'{self.bestValue:.3f}')

    def UpdateCandidateLabel(self, candidate):
        self.candidateEdit.setText(candidate)

    def UpdateMetrics(self, updateRunTimeSignal: Signal):
        while True:
            if self.ID in runningActions:
                tm = time.time()
                if not runningActions[self.ID][0].is_set():
                    self.runTimeAmount += tm - self.t0
                    updateRunTimeSignal.emit(self.runTimeAmount)
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
        self.variableNameToID = dict()
        self.immediateObjectiveName = f'{self.objectives[0].name} (ID: {self.objectives[0].ID})'
        for _, d in enumerate(self.decisions):
            self.activeDims[d.ID] = _
            nm = f'{d.name} (ID: {d.ID})'
            variables[nm] = [d.settings['components']['value']['min'], d.settings['components']['value']['max']]
            self.variableNameToID[nm] = d.ID
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
        # random samples
        numSamples = max(self.settings['numSamples'], 1)
        self.X.random_evaluate(numSamples)
        numEvals = 0
        while True:
            newNumEvals = self.numEvals
            if newNumEvals > numEvals:
                numEvals = newNumEvals
                self.progressAmount = numEvals / self.maxEvals
                self.updateProgressSignal.emit(self.progressAmount)
                self.updateAverageSignal.emit(np.nanmean(self.lastValues))
                self.updateBestSignal.emit(self.bestValue)
            if numEvals == numSamples:
                break
            if self.stopCheckThread.wait(timeout = .1):
                break
        shared.workspace.assistant.PushMessage(f'{self.name} has taken initial random samples.')
        print('Done with random samples!')
        # optimiser steps
        if self.settings['numSteps'] > 0:
            for it in range(self.settings['numSteps']):
                print(f'step {it + 1}/{self.settings['numSteps']}')
                self.X.step()
                self.X.generator.train_model()
                self.progressAmount = self.numEvals / self.maxEvals
                self.updateProgressSignal.emit(self.progressAmount)
                self.updateAverageSignal.emit(np.nanmean(self.lastValues))
                self.updateBestSignal.emit(self.bestValue)
                idx = np.argmax(self.X.data.iloc[:, -3]) if self.settings['mode'].upper() == 'MAXIMISE' else np.argmin(self.X.data.iloc[:, -3])
                self.updateCandidateSignal.emit('  '.join([f'{num:.3f}' for num in self.X.data.iloc[idx, :-3]]))
                # allow user to break out of this for loop.
                if self.stopCheckThread.wait(timeout = .1):
                    break
        shared.workspace.assistant.PushMessage(f'{self.name} has finished.')
        print('Done with optimiser steps!')
        self.inQueue.put(None)

    def Start(self, changeGlobalToggleState = True, **kwargs):
        if self.ID in runningActions:
            if runningActions[self.ID][0].is_set():
                shared.workspace.assistant.PushMessage(f'{self.name} has resumed.')
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
        for o in self.fundamentalObjectives:
            if isinstance(o, Number): # ignore numbers as settable values.
                self.fundamentalObjectives.pop(self.fundamentalObjectives.index(o))
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

        runningActions[self.ID] = [Event(), Event(), Event(), 0.] # pause, stop, error, progress
        if self.online:
            CreatePersistentWorker(self, emptyArray, self.inQueue, self.outQueue, self.SendMachineInstructions, 0.)
        else:
            worker = Thread(target = CreatePersistentWorker, args = (self, emptyArray, self.inQueue, self.outQueue, self.Simulate), kwargs = {'dtype': precision})
            worker.start()
        # SetGlobalToggleState()

        def Evaluate(dictIn: dict):
            for v in dictIn:
                shared.entities[self.variableNameToID[v]].data[0] = dictIn[v]
                shared.entities[self.variableNameToID[v]].data[1] = dictIn[v]
            self.inQueue.put(dictIn)
            simResult = self.outQueue.get()
            if simResult is None: # stop was triggered
                return {immediateObjectiveName: np.nan}
            for it, o in enumerate(self.fundamentalObjectives):
                o.data[1] = simResult[it]
            self.objectives[0].Start()
            if self.initialised:
                with self.lock:
                    if self.lastValues.shape[0] > self.runningAverageWindow:
                        self.lastValues = np.delete(self.lastValues, 0)
                    self.lastValues = np.append(self.lastValues, np.array([self.objectives[0].data[1]]))
                if self.settings['mode'].upper() == 'MAXIMISE':
                    with self.lock:
                        if self.bestValue is None or self.bestValue < self.objectives[0].data[1]:
                            self.bestValue = self.objectives[0].data[1]
                elif self.settings['mode'].upper() == 'MINIMISE':
                    with self.lock:
                        if self.bestValue is None or self.bestValue > self.objectives[0].data[1]:
                            self.bestValue = self.objectives[0].data[1]
            with self.lock:
                self.numEvals += 1
            
            return {immediateObjectiveName: self.objectives[0].data[1]}

        self.timestamp.setText(self.Timestamp())
        self.progressEdit.setText('0')
        self.bestEdit.setText('N/A')
        self.candidateEdit.setText('N/A')
        self.averageEdit.setText('N/A')
        self.numEvals = 0
        self.stopCheckThread.clear()
        Thread(target = self.SetupAndRunOptimiser, args = (Evaluate,), daemon = True).start()
        Thread(target = self.UpdateMetrics, args = (self.updateRunTimeSignal,), daemon = True).start()

    def Pause(self, changeGlobalToggleState = True):
        with self.lock:
            if not self.actionFinished.is_set():
                if self.ID in runningActions and not runningActions[self.ID][0].is_set():
                    TogglePause(self, changeGlobalToggleState)
                    if runningActions[self.ID][0].is_set():
                        shared.workspace.assistant.PushMessage(f'{self.name} is paused.')
                        self.progressBar.TogglePause(True)
                    else:
                        shared.workspace.assistant.PushMessage(f'{self.name} is running.')
                        self.progressBar.TogglePause(False)

    def Reset(self):
        self.stopCheckThread.set()
        self.isReset = True
        super().Reset()
        self.progressBar.Reset()
        shared.workspace.assistant.PushMessage(f'{self.name} has been reset.')

    def Stop(self):
        StopAction(self)

    def SendMachineInstructions(self, pause, stop, error, progress, sharedMemoryName, shape, dtype, parameters, **kwargs):
        if not self.sharedMemoryCreated:
            self.sharedMemory = SharedMemory(name = sharedMemoryName)
            self.sharedMemoryCreated = True
        data = np.ndarray(shape, dtype, buffer = self.sharedMemory.buf)
        print('== Send Machine Instructions ==')
        for d in parameters:
            nm = d.split()[:-1]
            print(f'{nm} is being set to {parameters[d]:.3f}')
        print('-------')


    def Simulate(self, pause, stop, error, sharedMemoryName, shape, parameters, **kwargs):
        '''Action does this:
            1. Track Beam
            2. Store objectives vector in data
            3. Return
        '''
        dtype = kwargs.pop('dtype', np.float32)
        numRepeats = 5
        self.simulator.numParticles = self.numParticles
        if not self.sharedMemoryCreated:
            self.sharedMemory = SharedMemory(name = sharedMemoryName)
            self.sharedMemoryCreated = True
        data = np.ndarray(shape = shape, dtype = dtype, buffer = self.sharedMemory.buf)
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
                        return None
                    time.sleep(.1)
                if stop.is_set():
                    self.sharedMemory.close()
                    self.sharedMemory.unlink()
                    return None
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