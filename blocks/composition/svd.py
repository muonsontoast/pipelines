from PySide6.QtWidgets import QGraphicsProxyWidget, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt
import numpy as np
from scipy.linalg import svd
from copy import deepcopy
from .composition import Composition
from ...components.slider import SliderComponent
from ...ui.runningcircle import RunningCircle
from ...actions.offline.svd import SVDAction
from ...utils.multiprocessing import PerformAction, TogglePause, StopAction
from ... import shared
from ... import style

class SVD(Composition):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(parent, proxy, name = kwargs.pop('name', 'SVD'), type = 'SVD', size = kwargs.pop('size', [500, 200]), **kwargs)
        self.AddButtons('pause', 'stop','clear')
        self.start.setText('Calculate Trajectory')
        self.s, self.U, self.VT = np.zeros(0,), np.zeros(0,), np.zeros(0,)
        self.correctors = dict()
        self.BPMs = dict()
        print('self.s has length:', len(self.s))
        self.settings['components'] = {
            'truncation': dict(name = 'truncation', value = max(len(self.s), 1), min = 1, max = max(1, len(self.s)), default = len(self.s), units = '', valueType = int, type = SliderComponent)
        }
        self.offlineAction = SVDAction()
        self.runningCircle = RunningCircle()
        self.header.layout().addWidget(self.runningCircle, alignment = Qt.AlignRight)
        self.CreateSection('truncation', 'Singular Vector Truncation', self.settings['components']['truncation']['max'], 0)

        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))

        def func(d: dict, **kwargs):
            self.PerformSVD()
            d['xticks01'] = np.arange(len(self.s))
            d['xticklabels01'] = [v + 1 for v in range(len(self.s))]
            d['data'] = self.s
            d['s'] = self.s
            d['U'] = self.U
            d['VT'] = self.VT
            d['trajectory'] = self.data # list of x, y tuples
            return d

        self.streams = {
            'default': lambda **kwargs: func({
                'xlabel01': 'Singular Vector',
                'ylabel01': 'Singular Value',
                'xlabel02': r'$s$ (m)',
                'ylabel02': r'$\Delta~$Beam Centre (mm)',
                'plottype': 'SVD',
            }),
        }
        # override in socket acceptable types
        self.inSocket.socket.acceptableTypes = ['Orbit Response']
        self.ToggleStyling(active = False)

    def PerformSVD(self):
        '''Returns just singular values, but all data can be easily accessed.'''
        data = shared.entities[next(iter(self.linksIn))].streams['default']()['data']
        if data.shape != (0,):
            self.U, self.s, self.VT = svd(shared.entities[next(iter(self.linksIn))].streams['default']()['data'])

    def Start(self):
        # Sort the correctors and BPMs to produce a proper ORM (Index -> Alignment)
        if len(self.linksIn) == 0:
            return
        ORMEntity = shared.entities[next(iter(self.linksIn))]
        # copy correctors and BPMs of the ORM linked to this
        self.correctors = ORMEntity.correctors
        self.BPMs = ORMEntity.BPMs
        # reset view block if attached
        for ID in self.linksOut:
            if shared.entities[ID].type == 'View':
                shared.entities[ID].firstDraw = True
        
        if not self.online:
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
                np.empty((len(self.BPMs), 3)), # list of tuples where x0 = x, and x1...n are y values for different methods.
            ):
                shared.workspace.assistant.PushMessage('SVD trajectory calculation already running.', 'Error')

    def AddLinkIn(self, ID, socket):
        # SVD only accepts ORM blocks so just collect those correctors and BPMs
        self.correctors = shared.entities[ID].correctors
        self.BPMs = shared.entities[ID].BPMs
        # update canRun flag
        if self.correctors and self.BPMs:
            self.canRun = True
        super().AddLinkIn(ID, socket)
        self.PerformSVD() # update the U, s and VT arrays
        self.settings['components']['truncation']['value'] = len(self.s)
        self.settings['components']['truncation']['max'] = len(self.s)
        self.settings['components']['truncation']['default'] = len(self.s)
        # Update sliders
        self.truncationAmount.SetMaximum(True)
        self.truncationAmount.SetDefault(True)

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            pass
        super().BaseStyling()

    def SelectedStyling(self):
        pass