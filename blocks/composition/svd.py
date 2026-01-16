from PySide6.QtWidgets import QGraphicsProxyWidget, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QTimer
import numpy as np
from scipy.linalg import svd
from copy import deepcopy
from .composition import Composition
from ...components.slider import SliderComponent
from ...ui.runningcircle import RunningCircle
from ...actions.offline.svd import SVDAction
from ...utils.multiprocessing import PerformAction
from ... import shared

class SVD(Composition):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(parent, proxy, name = kwargs.pop('name', 'SVD'), type = 'SVD', size = kwargs.pop('size', [500, 200]), **kwargs)
        self.AddButtons('pause', 'stop','clear')
        self.start.setText('Calculate Trajectory')
        self.s, self.U, self.VT = np.zeros(0,), np.zeros(0,), np.zeros(0,)
        self.correctors = dict()
        self.BPMs = dict()
        self.settings['components'] = {
            'truncation': dict(name = 'truncation', value = max(len(self.s), 1), min = 1, max = max(1, len(self.s)), default = len(self.s), units = '', valueType = int, type = SliderComponent),
        }
        self.offlineAction = SVDAction(self)
        self.runningCircle = RunningCircle()
        self.header.layout().addWidget(self.runningCircle, alignment = Qt.AlignRight)
        self.CreateSection('truncation', 'Singular Vector Truncation', self.settings['components']['truncation']['max'], 0)

        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))

        def func(d: dict, **kwargs):
            d['xticks01'] = np.arange(len(self.s))
            d['xticklabels01'] = [v + 1 for v in range(len(self.s))]
            d['data'] = self.s
            d['U'] = self.U
            d['VT'] = self.VT
            if not np.isinf(self.data).all():
                xTrajectory = []
                yTrajectory = []
                for it, BPM in enumerate(self.BPMs.values()):
                    if BPM.settings['alignment'] == 'Horizontal':
                        xTrajectory.extend([self.data[it]])
                    else:
                        yTrajectory.extend([self.data[it]])
                d['xTrajectory'] = np.array(sorted(xTrajectory, key = lambda point: point[0])) # list of s, x tuples
                d['yTrajectory'] = np.array(sorted(yTrajectory, key = lambda point: point[0])) # list of s, y tuples
            return d

        def evecs():
            d = dict()
            ORMID = next(iter(self.linksIn))
            ORMData = shared.entities[ORMID].streams[self.streamTypesIn[ORMID]]()
            d['data'] = self.VT[:self.settings['components']['truncation']['value']] if self.VT.shape[0] > 0 else self.data
            d['defaults'] = ORMData['defaults']
            d['lims'] = ORMData['lims']
            d['alignments'] = ORMData['alignments']
            d['linkedIdxs'] = ORMData['linkedIdxs']
            d['names'] = ORMData['names']
            return d

        self.streams = {
            'default': lambda: func({
                'xlabel01': 'Singular Vector',
                'ylabel01': 'Singular Value',
                'xlabel02': r'$s$ (m)',
                'ylabel02': r'$\Delta~$Beam Centre (mm)',
                'plottype': 'SVD',
            }),
            'evecs': lambda: evecs(),
        }
        self.inSocket.socket.acceptableTypes = ['Orbit Response']
        self.ToggleStyling(active = False)

    def PerformSVD(self):
        '''Returns just singular values, but all data can be easily accessed.'''
        data = shared.entities[next(iter(self.linksIn))].streams['default']()['data']
        if data.shape != (0,):
            self.U, self.s, self.VT = svd(shared.entities[next(iter(self.linksIn))].streams['default']()['data'])

    def Start(self, setpoints:np.ndarray = None, **kwargs):
        # Sort the correctors and BPMs to produce a proper ORM (Index -> Alignment)
        if len(self.linksIn) == 0:
            return
        ORMEntity = shared.entities[next(iter(self.linksIn))]
        for ID in self.linksOut:
            if shared.entities[ID].type == 'View':
                shared.entities[ID].firstDraw = True
        
        if setpoints is None:
            # will be deprecated in the future ...
            inputs = [{'ID': ORMEntity.ID, 'stream': self.streamTypesIn[ORMEntity.ID]}]
            self.offlineAction.ReadDependents(inputs)
        else:
            if not self.online:
                for it, c in enumerate(ORMEntity.correctors.values()):
                    c.Start(setpoint = setpoints[it], child = self)

        def WaitForResults():
            if not self.offlineAction.resultsWritten:
                self.title.setText(f'{self.title.text().split(' (')[0]} (Waiting)')
                return QTimer.singleShot(self.offlineAction.timeBetweenPolls, WaitForResults)
            else:
                if not self.online:
                    if setpoints is None:
                        self.PerformSVD()
                        self.offlineAction.correctors = self.correctors
                        self.offlineAction.BPMs = self.BPMs
                        self.offlineAction.lattice = deepcopy(shared.lattice)
                        self.offlineAction.U = self.U
                        self.offlineAction.s = self.s
                        self.offlineAction.VT = self.VT
                        if not self.offlineAction.CheckForValidInputs():
                            return
                        if not PerformAction(
                            self, 
                            np.empty((len(self.BPMs), 2)), # list of tuples where x0 = x, and x1...n are y values for different methods.
                        ):
                            shared.workspace.assistant.PushMessage('SVD trajectory calculation already running.', 'Error')
                        
                        def WaitForActionToFinish():
                            if np.isinf(self.data).any():
                                self.title.setText(f'{self.title.text().split(' (')[0]} (Running)')
                                QTimer.singleShot(100, WaitForActionToFinish)
                                return
                            
                        WaitForActionToFinish()

        WaitForResults()
        print('Finished setting / getting setpoints of correctors.')

    def AddLinkIn(self, ID, socket):
        # SVD only accepts ORM blocks so just collect those correctors and BPMs
        self.correctors = shared.entities[ID].correctors
        self.BPMs = shared.entities[ID].BPMs
        # update canRun flag
        if self.correctors and self.BPMs:
            self.canRun = True
        super().AddLinkIn(ID, socket, 'raw')
        ORMEntity = shared.entities[next(iter(self.linksIn))]
        if not np.isinf(ORMEntity.data).any():
            self.PerformSVD() # update the U, s and VT arrays
        singularValues = min(len(ORMEntity.correctors), len(ORMEntity.BPMs))
        self.settings['components']['truncation']['value'] = singularValues
        self.settings['components']['truncation']['max'] = singularValues
        self.settings['components']['truncation']['default'] = singularValues
        # Update sliders
        self.truncationAmount.SetMaximum(True)
        self.truncationAmount.SetDefault(True)
        return True

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            pass
        super().BaseStyling()

    def SelectedStyling(self):
        pass