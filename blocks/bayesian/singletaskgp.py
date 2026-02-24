from PySide6.QtWidgets import QWidget, QPushButton, QLineEdit, QComboBox, QLabel, QSizePolicy, QHBoxLayout, QVBoxLayout, QSpacerItem
from PySide6.QtCore import Qt, Signal
import numpy as np
import operator
from functools import reduce
import asyncio
import aioca
import time
import warnings
import pandas as pd
from datetime import datetime
from xopt import Xopt, VOCS, Evaluator
from xopt.generators.bayesian import UpperConfidenceBoundGenerator, ExpectedImprovementGenerator
from xopt.generators.bayesian.models.standard import StandardModelConstructor
from multiprocessing import Event
from threading import Event as ThreadingEvent
from multiprocessing.shared_memory import SharedMemory
from threading import Thread, Lock
from queue import Queue
from pathlib import Path
from ...simulator import Simulator
from ... import shared
from ..draggable import Draggable
from ...utils import cothread
# PerformAction is invoked when running tasks in offline mode to keep the UI responsive.
from ...utils.multiprocessing import SetGlobalToggleState, TogglePause, StopAction, CreatePersistentWorkerProcess, CreatePersistentWorkerThread, runningActions
from ..filters.filter import Filter
from ..constraints.constraint import Constraint
from ..number import Number
from ..pv import PV
from ..progress import Progress
from ... import style
from ... import shared
warnings.filterwarnings('ignore')

class SingleTaskGP(Draggable):
    updateProgressSignal = Signal(float)
    updateRunTimeSignal = Signal(float)
    updateAverageSignal = Signal(float)
    updateBestSignal = Signal(float)
    updateCandidateSignal = Signal(str)
    updateTuRBOSignal = Signal(str)
    updateAssistantSignal = Signal(str, str)

    def __init__(self, parent, proxy, **kwargs):
        # sim numerical precision set to fp32 by default to allow much higher particle populations.
        simPrecision = kwargs.pop('simPrecision', None)
        if simPrecision is None or simPrecision == 'fp32':
            simPrecision = 'fp32'
        elif simPrecision == 'fp64':
            simPrecision = 'fp64'

        super().__init__(
            proxy, name = kwargs.pop('name', 'Single Task GP'), type = 'Single Task GP', size = kwargs.pop('size', [600, 665]), 
            acqFunction = kwargs.pop('acqFunction', 'UCB'),
            acqHyperparameter = kwargs.pop('acqHyperparameter', 2),
            numSamples = kwargs.pop('numSamples', 5),
            numSteps = kwargs.pop('numSteps', 20),
            mode = kwargs.pop('mode', 'MAXIMISE'),
            turbo = kwargs.pop('turbo', 'DISABLED'),
            numParticles = kwargs.pop('numParticles', 5000),
            simPrecision = simPrecision,
            headerColor = "#a4243b",
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
        self.updateAssistantSignal.connect(self.UpdateAssistant)
        self.updateTuRBOSignal.connect(self.UpdateTuRBO)

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
            'constraints': [
                {
                    'name': c.settings['linkedElement'].Name,
                    'index': c.settings['linkedElement'].Index,
                    's': c.settings['linkedElement']['s (m)'],
                    'dtype': c.settings['dtype'],
                }
                for c in self.fundamentalConstraints
            ],
            'observers': [
                {
                    'index': o.settings['linkedElement'].Index,
                    'dtype': o.settings['dtype'],
                }
                for o in self.observers
            ],
            'numParticles': self.numParticles,
            'totalSteps': self.settings['numSamples'] + self.settings['numSteps'],
            'numObjectives': self.numFundamentalObjectives,
            'numConstraints': self.numFundamentalConstraints,
            'numObservers': self.numObservers,
        }

    def __setstate__(self, state):
        self.lattice = state['lattice']
        self.simulator = Simulator(lattice = self.lattice)
        self.decisions:list = state['decisions']
        self.objectives:list = state['objectives']
        self.constraints:list = state['constraints']
        self.observers:list = state['observers']
        self.numObjectives:int = state['numObjectives']
        self.numConstraints:int = state['numConstraints']
        self.numObservers:int = state['numObservers']
        self.sharedMemoryCreated = False
        self.totalSteps = state['totalSteps']
        if 'numParticles' in state:
            self.numParticles = state['numParticles']
            self.computations = {
                'CHARGE': self.GetCharge,
                'X': self.GetX,
                'Y': self.GetY,
                'XP': self.GetXP,
                'YP': self.GetYP,
                'SURVIVAL_RATE': self.GetSurvivalRate,
            }

    def Push(self):
        from ..composition.composition import Composition
        from ..kernels.kernel import Kernel
        super().Push()
        self.widget.layout().setContentsMargins(5, 10, 20, 10)
        self.widget.layout().setSpacing(20)
        self.AddSocket('decision', 'F', 'Decision', 185, acceptableTypes = [PV])
        self.AddSocket('objective', 'F', 'Objective', 185, acceptableTypes = [PV, Composition, Filter])
        self.AddSocket('constraint', 'F', 'Constraint', 185, acceptableTypes = [Constraint])
        self.AddSocket('kernel', 'F', 'Kernel', 185, acceptableTypes = [Kernel, Composition, Filter])
        self.AddSocket('prior', 'F', 'Prior', 185, acceptableTypes = [Draggable])
        self.AddSocket('out', 'M')
        self.content = QWidget()
        self.content.setLayout(QVBoxLayout())
        self.content.layout().setContentsMargins(0, 0, 0, 0)
        self.content.layout().setSpacing(25)
        self.widget.layout().addWidget(self.content)
        # settings section
        settings = QWidget()
        settings.setFixedHeight(235)
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
        acquisitionLabel = QLabel('Generator')
        acquisitionLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        acquisitionLabel.setAlignment(Qt.AlignLeft)
        acquisition.layout().addWidget(acquisitionLabel, alignment = Qt.AlignLeft | Qt.AlignVCenter)
        acquisitionSelect = QComboBox()
        acquisitionSelect.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        acquisitionSelect.setStyleSheet(style.ComboStyle(color = '#1e1e1e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 12))
        acquisitionSelect.view().parentWidget().setStyleSheet('color: transparent;')
        acquisitionFuncs = {
            '   UCB': self.SelectUCB,
            '   EI': self.SelectEI,
            # '   Explore': self.SelectBayesianExploration,
        }
        acquisitionSelect.addItems(acquisitionFuncs.keys())
        idx = 0 if self.settings['acqFunction'] == 'UCB' else 1
        acquisitionSelect.setCurrentIndex(idx)
        acquisitionSelect.currentTextChanged.connect(lambda: acquisitionFuncs[acquisitionSelect.currentText()]())
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
        # turbo
        turbo = QWidget()
        turbo.setFixedHeight(30)
        turbo.setLayout(QHBoxLayout())
        turbo.layout().setContentsMargins(5, 0, 0, 0)
        turboLabel = QLabel('TuRBO')
        turboLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', fontSize = 12))
        turboLabel.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        turbo.layout().addWidget(turboLabel)
        turboSelect = QComboBox()
        turboSelect.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        turboSelect.setStyleSheet(style.ComboStyle(color = '#1e1e1e', fontColor = '#c4c4c4', borderRadius = 6, fontSize = 12))
        turboSelect.view().parentWidget().setStyleSheet('color: transparent')
        turboFuncs = {
            '   DISABLED': self.DisableTuRBO,
            '   OPTIMISE': self.SelectTuRBOOptimise,
            '   SAFETY': self.SelectTuRBOSafety,
        }
        turboSelect.addItems(turboFuncs.keys())
        if self.settings['turbo'] == 'DISABLED':
            idx = 0
        elif self.settings['turbo'] == 'OPTIMISE':
            idx = 1
        else:
            idx = 2
        turboSelect.setCurrentIndex(idx)
        turboSelect.currentTextChanged.connect(lambda: turboFuncs[turboSelect.currentText()]())
        turbo.layout().addWidget(turboSelect)
        settings.layout().addWidget(turbo)
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

    def UpdateTuRBO(self, mode):
        shared.workspace.assistant.PushMessage(f'TuRBO mode on {self.name} was set to {mode}.')
    
    def UpdateAssistant(self, message, messageType = ''):
        if messageType == '':
            shared.workspace.assistant.PushMessage(message)
        else:
            shared.workspace.assistant.PushMessage(message, messageType)

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

    def Timestamp(self, includeDate = False, stripColons = False):
        if includeDate:
            timestamp = datetime.now().strftime('%Y-%m-%d__%H:%M:%S')
        else:
            timestamp = datetime.now().strftime('%H:%M:%S')
        if stripColons:
            timestamp = '-'.join(timestamp.split(':'))
        return timestamp

    def ChangeMode(self):
        self.settings['mode'] = 'MAXIMISE' if self.settings['mode'] == 'MINIMISE' else 'MINIMISE'
        self.modeLabel.setText(f'Mode:\t{self.settings['mode']}')
        self.updateAssistantSignal.emit(f'Successfully changed mode of {self.name} to {self.settings['mode']}.', '')

    def ChangeAcqHyperparameter(self):
        try:
            val = float(self.explorationEdit.text())
        except:
            self.updateAssistantSignal.emit(f'Failed to change the acquisition function exploration hyperparameter of {self.name} because it isn\'t an int or float.', 'Error')
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
        self.updateAssistantSignal.emit(f'Successfully changed the acquisition function exploration hyperparameter of {self.name} to {newText}.', '')

    def ChangeSamples(self):
        try:
            val = round(float(self.samplesEdit.text()))
        except:
            self.updateAssistantSignal.emit(f'Failed to change the number of initial random samples of {self.name} because it isn\'t an int or float.', 'Error')
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
        self.updateAssistantSignal.emit(f'Successfully changed the number of initial random samples of {self.name} to {newText}.', '')

    def ChangeSteps(self):
        try:
            val = round(float(self.stepsEdit.text()))
        except:
            self.updateAssistantSignal.emit(f'Failed to change the number of steps of {self.name} because it isn\'t an int or float.', 'Error')
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
        self.updateAssistantSignal.emit(f'Successfully changed the maximum number of steps of {self.name} to {newText}.', '')

    def SelectUCB(self):
        self.settings['acqFunction'] = 'UCB'
        self.explorationEdit.setText(f'{self.settings['acqHyperparameter']:.1f}')
        self.explorationEdit.setReadOnly(False)
        self.updateAssistantSignal.emit(f'Successfully changed the acquisition function of {self.name} to UCB (Upper Confidence Bound).', '')

    def SelectEI(self):
        self.settings['acqFunction'] = 'EI'
        self.explorationEdit.setText('N/A')
        self.explorationEdit.setReadOnly(True)
        self.updateAssistantSignal.emit(f'Successfully changed the acquisition function of {self.name} to EI (Expected Improvement).', '')

    def SelectBayesianExploration(self):
        self.settings['acqFunction'] = 'BayesianExploration'
        self.explorationEdit.setText('N/A')
        self.explorationEdit.setReadOnly(True)

    def DisableTuRBO(self):
        if self.settings['turbo'] != 'DISABLED':
            self.updateTuRBOSignal.emit('DISABLED')
        self.settings['turbo'] = 'DISABLED'

    def SelectTuRBOOptimise(self):
        if self.settings['turbo'] != 'OPTIMISE':
            self.updateTuRBOSignal.emit('OPTIMISE')
        self.settings['turbo'] = 'OPTIMISE'
    
    def SelectTuRBOSafety(self):
        # Safety mode is only valid if at least one constraint is specified.
        valid = False
        for ID, link in self.linksIn.items():
            if link['socket'] == 'constraint':
                valid = True
                break
        if not valid:
            self.updateAssistantSignal.emit(f'SAFETY is not a valid mode of {self.name} because it has no constraints.', 'Warning')
            return
        if self.settings['turbo'] != 'SAFETY':
            self.updateTuRBOSignal.emit('SAFETY')
        self.settings['turbo'] = 'SAFETY'

    def ConstructKernel(self):
        '''Traces the kernel structure up the pipeline and returns an Xopt compatible composition.'''
        # fetch the block attached to the kernel socket
        kernel = [ID for ID, link in self.linksIn.items() if link['socket'] == 'kernel' and shared.entities[ID].type != 'Group'][0] # assume a single match for now ... (will be replaced)
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
        from gpytorch.kernels import RBFKernel as _RBFKernel, PeriodicKernel as _PeriodicKernel, MaternKernel as _MaternKernel, ScaleKernel
        from ..kernels.rbf import RBFKernel
        from ..kernels.periodic import PeriodicKernel
        from ..kernels.matern import MaternKernel
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
        elif isinstance(entity, MaternKernel):
            if entity.settings['automatic']:
                return ScaleKernel(_MaternKernel(nu = entity.settings['hyperparameters']['smoothness']['value']))
            return ScaleKernel(_MaternKernel(active_dims = sorted([self.activeDims[linkedPVID] for linkedPVID in entity.settings['linkedPVs']])))

    def GetFundamentalIDs(self, ID, fundamentalIDs = set([]), socketNameFilter = None):
        entity = shared.entities[ID]
        linksIn = [linkID for linkID, v in entity.linksIn.items() if v['socket'] == socketNameFilter] if socketNameFilter is not None else [linkID for linkID, v in entity.linksIn.items()]
        if len(linksIn) > 0:
            for linkID in linksIn:
                fundamentalIDs = fundamentalIDs.union(self.GetFundamentalIDs(linkID, fundamentalIDs)) # union set with newly found objectives
            return list(fundamentalIDs)
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
    
    def GetBestRow(self):
        if not self.notAllNaNs:
            self.bestRowIdx = None
            self.bestRow = None
            return
        if self.numConstraints > 0:
            try:
                cond = []
                for c in self.constraints:
                    if c.type == '< (Constraint)':
                        for ID in c.linksIn:
                            if shared.entities[ID].type == 'Group':
                                continue
                            cond.append(self.X.data[self.constraintsIDToName[ID]] < c.settings['threshold'])
                    else:
                        for ID in c.linksIn:
                            if shared.entities[ID].type == 'Group':
                                continue
                            cond.append(self.X.data[self.constraintsIDToName[ID]] > c.settings['threshold'])
                mask = np.logical_and.reduce(cond)
                if self.settings['mode'].upper() == 'MAXIMISE':
                    self.bestRowIdx = self.X.data[mask][self.immediateObjectiveName].idxmax()
                else:
                    self.bestRowIdx = self.X.data[mask][self.immediateObjectiveName].idxmin()
                self.bestRow = self.X.data.loc[self.bestRowIdx]
            except:
                self.bestRow = None
        else:
            try:
                if self.settings['mode'].upper() == 'MAXIMISE':
                    self.bestRow = self.X.data.loc[self.X.data[self.immediateObjectiveName].idxmax()]
                else:
                    self.bestRow = self.X.data.loc[self.X.data[self.immediateObjectiveName].idxmin()]
            except:
                self.bestRow = None

    def UpdateBestMetrics(self):
        if self.bestRow is not None:
            with self.lock:
                if self.lastValues.shape[0] > self.runningAverageWindow:
                    self.lastValues = np.delete(self.lastValues, 0)
                self.lastValues = np.append(self.lastValues, np.array([self.X.data[self.immediateObjectiveName].iloc[-1]]))
            try:
                self.bestValue = self.bestRow.iloc[self.numDecisions]
                self.updateCandidateSignal.emit('  '.join([f'{num:.3f}' for num in self.bestRow.iloc[:self.numDecisions]]))
                self.updateAverageSignal.emit(np.nanmean(self.lastValues))
                self.updateBestSignal.emit(self.bestValue)
            except:
                pass
            
    def SetupAndRunOptimiser(self, evaluateFunction):
        try:
            self.updateAssistantSignal.emit(f'{self.name} is setting up for the first time, which may take a few seconds.', '')
            mode = 'MAXIMIZE' if self.settings['mode'].upper() == 'MAXIMISE' else 'MINIMIZE'
            variables = dict()
            self.variableNameToID = dict()
            self.optimiserConstraints = dict()
            self.constraintsIDToName = dict()
            self.immediateObjectiveName = f'{self.objectives[0].name} (ID: {self.objectives[0].ID})'
            self.observerValues = np.zeros((self.settings['numSamples'] + self.settings['numSteps'], self.numObservers))
            for _, d in enumerate(self.decisions):
                if d.type == 'Group':
                    continue
                self.activeDims[d.ID] = _
                nm = f'{d.name} (ID: {d.ID})'
                variables[nm] = [d.settings['components']['value']['min'], d.settings['components']['value']['max']]
                self.variableNameToID[nm] = d.ID
            # Treat each block attached to a constraint as its own individual constraint.
            for _, c in enumerate(self.constraints):
                if c.type == 'Group':
                    continue
                for ID in c.linksIn:
                    if shared.entities[ID].type == 'Group':
                        continue
                    nm = f'{shared.entities[ID].name} (ID: {ID})'
                    if c.type == '< (Constraint)':
                        self.optimiserConstraints[nm] = ['LESS_THAN', c.settings['threshold']]
                    else:
                        self.optimiserConstraints[nm] = ['GREATER_THAN', c.settings['threshold']]
                    self.constraintsIDToName[ID] = nm
            vocs = VOCS(
                variables = variables,
                objectives = {
                    self.immediateObjectiveName: mode,
                },
                constraints = self.optimiserConstraints,
            )
            kernel = self.ConstructKernel()
            constructor = StandardModelConstructor(
                covar_modules = {
                    self.immediateObjectiveName: kernel,
                },
            )
            generatorKwargs = dict(
                vocs = vocs,
                gp_constructor = constructor,
                n_monte_carlo_samples = 256,
                n_candidates = 10,
            )
            # TuRBO
            if self.settings['turbo'] == 'OPTIMISE':
                generatorKwargs['turbo_controller'] = 'optimize'
            elif self.settings['turbo'] == 'SAFETY':
                if len(self.constraints) > 0:
                    generatorKwargs['turbo_controller'] = 'safety'
                else:
                    generatorKwargs['turbo_controller'] = 'optimize'
                    self.updateAssistantSignal.emit(f'TuRBO mode of {self.name} is falling back to OPTIMISE because there are no constraints.', 'Warning')
            if self.settings['acqFunction'] == 'UCB':
                generatorKwargs['beta'] = self.settings['acqHyperparameter']
                generator = UpperConfidenceBoundGenerator(**generatorKwargs)
            else:
                generator = ExpectedImprovementGenerator(**generatorKwargs)
            if self.settings['turbo'] != 'DISABLED':
                generator.turbo_controller.length = (
                    .05 # 5% of the range.
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
            self.notAllNaNs = False
            timestamp = self.Timestamp(includeDate = True, stripColons = True)
            self.updateAssistantSignal.emit(f'{self.name} is now running.', '')
            try:
                self.X.random_evaluate(1) # run once to initialise shared memory array
            except Exception as e:
                print(e)

            self.initialised = True
            self.X.data.drop(0, inplace = True)
            self.numEvals = 0
            # random samples
            numSamples = max(self.settings['numSamples'], 1)
            if self.numObservers > 0:
                insertIdx = self.numDecisions + self.numFundamentalConstraints + self.numObjectives
                observerIDToName = {
                    o.ID: f'{o.name} (ID: {o.ID})'
                    for o in self.observers
                }
            #### JUST FOR NOW ...
            # numEvals = 0
            # for it in range(numSamples):
            #     self.X.random_evaluate(1)
            #     self.notAllNaNs = self.X.data.iloc[:, self.numDecisions:-2].notna().all(axis = 1).any()
            #     if self.numObservers > 0:
            #         dataToSave = self.X.data.copy()
            #         for it, o in enumerate(self.observers):
            #             dataToSave.insert(loc = insertIdx, column = observerIDToName[o.ID], value = self.observerValues[:self.numEvals, it])
            #         dataToSave.to_csv(Path(shared.cwd) / 'datadump' / f'{timestamp}.csv', index = False)
            #     else:
            #         self.X.data.to_csv(Path(shared.cwd) / 'datadump' / f'{timestamp}.csv', index = False)
            #     self.progressAmount = (numEvals + 1) / self.maxEvals
            #     self.updateProgressSignal.emit(self.progressAmount)
            #     numEvals += 1
            #     self.GetBestRow()
            #     self.UpdateBestMetrics()
            #     if self.CheckForInterrupt(runningActions[self.ID][0], runningActions[self.ID][1]):
            #         self.inQueue.put(None)
            #         self.inQueue.join()
            #         self.outQueue.join()
            #         return
                
            # For testing - add the known good solution ...
            if self.settings['turbo'] != 'DEFAULT':
                HSTRs = [.4178, -.4341, 3.27, .71, 3.5, -1.06]
                VSTRs = [3.8198, -4.18, -.28, .46, 1.1, 2.18]
                QUADs = [2.3857, -1.8666, -2.4557, 2.1872, 2.2825, 2.5736, -1.9105, 1.5804]
                # first two BPM trajectories are too large, constrain them.
                # BPMy = [-6, -2.5]
                BPMy = [6, 2.5]
                BPMx = [3, -1]
                best = 3.63
                self.X.data = pd.read_csv(Path(shared.cwd) / 'datadump' / '2026-02-24__17-25-23.csv')
                # self.X.add_data(pd.DataFrame([[*HSTRs[1:], VSTRs[-1], HSTRs[0], *(VSTRs[::-1][1:]), *QUADs[-4:], best, *BPMy, 0, False]], columns = self.X.data.columns))
            ####################
            
            # train the model on the LH samples and centre the trust region if TuRBO is being used.
            if self.notAllNaNs:
                self.X.generator.train_model()
                self.X.generator.turbo_controller.update_state(self.X.generator)

            self.updateAssistantSignal.emit(f'{self.name} has taken initial random samples.', '')
            # optimiser steps
            if self.settings['numSteps'] > 0:
                for it in range(self.settings['numSteps']):
                    print(f'step {it + 1}/{self.settings['numSteps']}')
                    self.notAllNaNs = self.X.data.iloc[:, self.numDecisions:-2].notna().all(axis = 1).any()
                    # if self.notAllNaNs:
                    try:
                        self.X.step()
                    except Exception as e: # TuRBO will fail if no solutions in the dataset satisfy all constraints or due to ill-conditioned matrix.
                        print(e)
                        self.X.random_evaluate(1)
                    # else:
                    #     self.X.random_evaluate(1)
                    # Handle observers if they exist.
                    if self.numObservers > 0:
                        dataToSave = self.X.data.copy()
                        for it, o in enumerate(self.observers):
                            dataToSave.insert(loc = insertIdx, column = observerIDToName[o.ID], value = self.observerValues[:self.numEvals, it])
                        dataToSave.to_csv(Path(shared.cwd) / 'datadump' / f'{timestamp}.csv', index = False)
                    else:
                        self.X.data.to_csv(Path(shared.cwd) / 'datadump' / f'{timestamp}.csv', index = False)
                    self.notAllNaNs = self.X.data.iloc[:, self.numDecisions:-2].notna().all(axis = 1).any()
                    self.progressAmount = self.numEvals / self.maxEvals
                    self.updateProgressSignal.emit(self.progressAmount)
                    try:
                        self.GetBestRow()
                        if self.bestRow is not None:
                            self.bestValue = self.bestRow.iloc[self.numDecisions]
                            with self.lock:
                                if self.lastValues.shape[0] > self.runningAverageWindow:
                                    self.lastValues = np.delete(self.lastValues, 0)
                                self.lastValues = np.append(self.lastValues, np.array([self.X.data[self.immediateObjectiveName].iloc[-1]]))
                            self.updateCandidateSignal.emit('  '.join([f'{num:.3f}' for num in self.bestRow.iloc[:self.numDecisions]]))
                            self.updateAverageSignal.emit(np.nanmean(self.lastValues))
                            self.updateBestSignal.emit(self.bestValue)
                    except Exception as e:
                        print(e)
                    if self.CheckForInterrupt(runningActions[self.ID][0], runningActions[self.ID][1], timeout = .1):
                        self.inQueue.put(None)
                        self.inQueue.join()
                        self.outQueue.join()
                        return
            if self.bestRow is None:
                if self.numConstraints > 0:
                    self.updateAssistantSignal.emit(f'{self.name} has finished, but it failed to find a candidate satisfying the constraints.', 'Warning')
                else:
                    self.updateAssistantSignal.emit(f'{self.name} has finished, but it only recorded NaNs.', 'Warning')
            else:
                if self.numConstraints > 0:
                    self.updateAssistantSignal.emit(f'{self.name} has finished and found a solution satisfying the constraints.', '')    
                else:
                    self.updateAssistantSignal.emit(f'{self.name} has finished and found a solution.', '')
            print('Done with optimiser steps!')
            # Handle observers if they exist.
            if self.numObservers > 0:
                dataToSave = self.X.data.copy()
                for it, o in enumerate(self.observers):
                    dataToSave.insert(loc = insertIdx, column = observerIDToName[o.ID], value = self.observerValues[:self.numEvals, it])
                dataToSave.to_csv(Path(shared.cwd) / 'datadump' / f'{timestamp}.csv', index = False)
            else:
                self.X.data.to_csv(Path(shared.cwd) / 'datadump' / f'{timestamp}.csv', index = False)
        except Exception as e:
            print(e)
        self.inQueue.put(None)

    def Start(self, changeGlobalToggleState = True, **kwargs):
        if self.ID in runningActions:
            if runningActions[self.ID][0].is_set():
                self.updateAssistantSignal.emit(f'{self.name} has resumed.', '')
                TogglePause(self, changeGlobalToggleState)
                self.progressBar.TogglePause(False)
            return
        self.isReset = False
        self.actionFinished.clear()
        self.progressBar.Reset()
        self.decisions = []
        self.constraints = []
        self.observers = []
        for ID, v in self.linksIn.items():
            if shared.entities[ID].type == 'Group':
                continue
            if v['socket'] == 'decision':
                self.decisions.append(shared.entities[ID])
            elif v['socket'] == 'constraint':
                self.constraints.append(shared.entities[ID])
        self.numDecisions = len(self.decisions)
        # objective leaf nodes that determine the final objective value witnessed by the block.
        self.fundamentalObjectives = [shared.entities[ID] for ID in self.GetFundamentalIDs(self.ID, socketNameFilter = 'objective')]
        self.numFundamentalObjectives = len(self.fundamentalObjectives)
        self.fundamentalConstraints = [shared.entities[ID] for ID in self.GetFundamentalIDs(self.ID, socketNameFilter = 'constraint')]
        self.numFundamentalConstraints = len(self.fundamentalConstraints)
        self.numConstraints = len(self.constraints)
        for o in self.fundamentalObjectives:
            if isinstance(o, Number): # ignore numbers as settable values.
                self.fundamentalObjectives.pop(self.fundamentalObjectives.index(o))
        for c in self.fundamentalConstraints:
            if isinstance(c, Number):
                self.fundamentalConstraints.pop(self.fundamentalConstraints.index(c))
        # objectives with immediate connections to this block.
        self.objectives = [shared.entities[k] for k, v in self.linksIn.items() if v['socket'] == 'objective' and shared.entities[k].type != 'Group']
        self.numObjectives = len(self.objectives)
        immediateObjectiveName = f'{self.objectives[0].name} (ID: {self.objectives[0].ID})'
        if not self.CheckDecisionStatesAgree():
            return
        # if decision variables are valid, fetch any observers
        # observers are taken to be any block in the same group that have no ingoing or outgoing sockets.
        if self.groupID is not None:
            for ID in shared.entities[self.groupID].settings['IDs']:
                if ID == self.ID:
                    continue
                if not isinstance(shared.entities[ID], PV):
                    continue
                numLinksIn = len(shared.entities[ID].linksIn)
                numLinksOut = len(shared.entities[ID].linksOut)
                if numLinksIn == 0 and (numLinksOut == 0 or (numLinksOut == 1 and next(iter(shared.entities[ID].linksOut)) == 'free')):
                    self.observers.append(shared.entities[ID])
        self.numObservers = len(self.observers)
        self.online = self.decisions[0].online
        self.numParticles = 5000
        self.numEvals = 0
        self.maxEvals = self.settings['numSamples'] + self.settings['numSteps']
        self.t0 = time.time()
        self.runTimeAmount = 0
        self.progressAmount = 0

        precision = np.float32 if self.settings['simPrecision'] == 'fp32' else np.float64
        emptyArray = np.empty(self.numFundamentalObjectives + self.numFundamentalConstraints + self.numObservers, dtype = precision)
        self.inQueue, self.outQueue = Queue(), Queue()

        if self.online:
            runningActions[self.ID] = [ThreadingEvent(), ThreadingEvent(), ThreadingEvent(), 0.] # pause, stop, error, progress
        else:
            runningActions[self.ID] = [Event(), Event(), Event(), 0.] # pause, stop, error, progress
        # # FOR TESTNG #
        # self.online = True
        # ##############
        if self.online:
            Thread(target = CreatePersistentWorkerThread, args = (self, self.inQueue, self.outQueue, self.SendMachineInstructions)).start()
        else:
            Thread(target = CreatePersistentWorkerProcess, args = (self, emptyArray, self.inQueue, self.outQueue, self.Simulate), kwargs = {'dtype': precision}).start()
        # SetGlobalToggleState()
        numFundamentalObjectives = len(self.fundamentalObjectives)

        def Evaluate(dictIn: dict):
            for v in dictIn:
                shared.entities[self.variableNameToID[v]].data[0] = dictIn[v]
                if not self.online:
                    shared.entities[self.variableNameToID[v]].data[1] = dictIn[v]
            self.inQueue.put(dictIn)
            result = self.outQueue.get()
            self.outQueue.task_done()
            if result is None: # stop was triggered
                return {immediateObjectiveName: np.nan}
            if not self.online:
                for it, o in enumerate(self.fundamentalObjectives):
                    o.data[1] = result[it]
                for it, c in enumerate(self.fundamentalConstraints):
                    c.data[1] = result[it + numFundamentalObjectives]
                for it, o in enumerate(self.observers):
                    o.data[1] = result[it + numFundamentalObjectives + self.numFundamentalConstraints]
                    self.observerValues[self.numEvals, it] = o.data[1]
                result = self.objectives[0].Start()
                constraints = dict([[self.constraintsIDToName[k], v] for c in self.constraints for k, v in c.Start().items()])
            else:
                numRepeats = 5 if 'numRepeats' not in self.settings else self.settings['numRepeats']
                result = np.zeros(numRepeats)
                constraints = []
                for r in range(numRepeats):
                    result[r] = self.objectives[0].Start()
                    constraints.append(dict([[self.constraintsIDToName[k], v] for c in self.constraints for k, v in c.Start().items()]))
                    # PVs in-app update their values at 5Hz, so poll less frequently than this to guarantee a new value appears if is due to do so.
                    if self.CheckForInterrupt(runningActions[self.ID][0], runningActions[self.ID][1], timeout = .25):
                        break
                # average over repeat observations
                result = np.nanmean(result)
                # average constraints across repeats
                newConstraints = {
                    k: sum(constraintDict[k] for constraintDict in constraints) / numRepeats
                    for k in constraints[0]
                }
                constraints = newConstraints

            #### Replace NaNs with large numbers to allow the optimiser to perform inference ####
            # for k, v in constraints.items():
            #     if np.isnan(v):
            #         constraints[k] = 1e5 if self.optimiserConstraints[k][0] == 'LESS_THAN' else -1e5
            with self.lock:
                self.numEvals += 1
            return {immediateObjectiveName: result, **constraints}

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
                        self.updateAssistantSignal.emit(f'{self.name} is paused.', '')
                        self.progressBar.TogglePause(True)
                    else:
                        self.updateAssistantSignal.emit(f'{self.name} is running.', '')
                        self.progressBar.TogglePause(False)

    def Reset(self):
        self.stopCheckThread.set()
        self.isReset = True
        super().Reset()
        self.progressBar.Reset()
        self.updateAssistantSignal.emit(f'{self.name} has been reset.', '')

    def Stop(self):
        StopAction(self)

    # def SendMachineInstructions(self, pause, stop, error, loop, parameters, **kwargs):
    def SendMachineInstructions(self, pause, stop, error, parameters, **kwargs):
        '''Results do not need to be sent back to the optimiser from here during online optimisation.'''
        try:
            for d, target in parameters.items():
                nm = d.split()[0] # strip the index attached to this PV name in the inDict
                try:
                    # if target < loop.run_until_complete(aioca.caget(nm + ':I')):
                    if target < asyncio.run(aioca.caget(nm + ':I')):
                        # loop.run_until_complete(
                        asyncio.run(
                            aioca.caput(nm + ':SETI', target - .2)
                        )
                except:
                    stop.set()
                    self.updateAssistantSignal.emit(f'{self.name} was unable to communicate with {nm}.', 'Warning')
                    return None
            if self.CheckForInterrupt(pause, stop, timeout = 2):
                return 1
            # loop.run_until_complete(
            for d, target in parameters.items():
                nm = d.split()[0]
                asyncio.run(
                    aioca.caput(nm + ':SETI', target)
                )
            self.CheckForInterrupt(pause, stop, timeout = 1)
        except :
            pass
        return 1

    def CheckForInterrupt(self, pause, stop, timeout = 0):
        '''Returns True if stop is triggered otherwise False'''
        t0 = time.time()
        while True:
            if stop.wait(timeout = .1):
                if hasattr(self, 'dataSharedMemory'):
                    self.sharedMemory.close()
                    self.sharedMemory.unlink()
                return True
            if time.time() - t0 > timeout:
                while pause.wait(timeout = .1):
                    if stop.wait(timeout = .1):
                        if hasattr(self, 'dataSharedMemory'):
                            self.sharedMemory.close()
                            self.sharedMemory.unlink()
                        return True
                break
        return False

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
        result = np.zeros((numRepeats, self.numObjectives + self.numConstraints + self.numObservers))
        for d in parameters:
            idx = int(d.split('Index: ')[1].split(')')[0])
            # convert steerer values to mrad.
            if 'HSTR' in d:
                self.lattice[idx].KickAngle[0] = parameters[d] * 1e-3
                self.simulator.lattice[idx].KickAngle[0] = parameters[d] * 1e-3
            elif 'VSTR' in d:
                self.lattice[idx].KickAngle[1] = parameters[d] * 1e-3
                self.simulator.lattice[idx].KickAngle[1] = parameters[d] * 1e-3
        for r in range(numRepeats):
            tracking, _ = self.simulator.TrackBeam(self.numParticles)
            # Important - set columns to NaN if any entries in column are NaN
            tracking[:, np.isnan(tracking).any(axis = 0)] = np.nan
            # Compute results
            for it, o in enumerate(self.objectives):
                result[r, it] = self.computations[o['dtype']](tracking, o['index'])
                self.CheckForInterrupt(pause, stop)
            for it, c in enumerate(self.constraints):
                result[r, it + self.numObjectives] = self.computations[c['dtype']](tracking, c['index'])
                self.CheckForInterrupt(pause, stop)
            for it, ob in enumerate(self.observers):
                result[r, it + self.numObjectives + self.numConstraints] = self.computations[ob['dtype']](tracking, ob['index'])
                self.CheckForInterrupt(pause, stop)
        np.copyto(data, np.nanmean(result, axis = 0))
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
            self.updateAssistantSignal.emit(f'{self.name} mode is set to {'Online' if self.online else 'Offline'}', '')
        else:
            self.updateAssistantSignal.emit(f'Online mode has been disabled because cothread is not available on your machine.', 'Warning')

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