import at
from at import lattice_pass
import numpy as np
from copy import deepcopy
from multiprocessing.shared_memory import SharedMemory
from ..action import Action
from ...simulator import Simulator
from ... import shared

class SVDAction(Action):
    '''Computes the trajectory of the beam for a given set of corrector strengths\n
    or the inverse problem of finding the set of corrector strengths producing a given offset in BPMs.'''
    def __init__(self):
        super().__init__()
        self.correctors = None
        self.BPMs = None
        self.ORM = None

    def __getstate__(self):
        return {
            'lattice': self.lattice,
            'BPMs': [
                {
                    'name': b.name,
                    'index': b.settings['linkedElement'].Index,
                    'pos': b.settings['linkedElement']['s (m)'],
                    'alignment': b.settings['alignment'],
                    'linkedElementAttrs': b.linkedElementAttrs,
                }
                for b in self.BPMs.values()
            ],
            'correctors': [
                {
                    'name': c.name,
                    'index': c.settings['linkedElement'].Index,
                    'alignment': c.settings['alignment'],
                    'value': c.settings['components']['value']['value'],
                    'default': c.settings['components']['value']['default'],
                    'linkedElementAttrs': c.linkedElementAttrs,
                }
                for c in self.correctors.values()
            ],
            'U': self.U,
            's': self.s,
            'VT': self.VT,
        }
    
    def __setstate__(self, state):
        self.lattice = state['lattice']
        self.BPMs = state['BPMs']
        self.correctors = state['correctors']
        self.U = state['U']
        self.s = state['s']
        self.VT = state['VT']
        self.simulator = Simulator()

    def CheckForValidInputs(self) -> bool:
        if len(self.BPMs) == 0:
            shared.workspace.assistant.PushMessage('Orbit Response is missing BPMs', 'Error')
            return False
        if len(self.correctors) == 0:
            shared.workspace.assistant.PushMessage('Orbit Response is missing correctors', 'Error')
            return False
        for c in self.correctors.values():
            if 'linkedElement' not in c.settings.keys():
                shared.workspace.assistant.PushMessage('One or more correctors have not been linked to lattice elements. Setup a connection in the inspector.', 'Error')
                return False
        for b in self.BPMs.values():
            if 'linkedElement' not in b.settings.keys():
                shared.workspace.assistant.PushMessage('One or more BPMs have not been linked to lattice elements. Setup a connection in the inspector.', 'Error')
                return False
        return True
    
    def Run(self, pause, stop, error, sharedMemoryName, shape, dtype, **kwargs):
        '''Computes the beam trajectory along the beamline.'''
        numParticles = kwargs.get('numParticles', 10000)
        sharedMemory = SharedMemory(name = sharedMemoryName)
        data = np.ndarray(shape, dtype, buffer = sharedMemory.buf)
        data[:, 0] = np.array([b['pos'] for b in self.BPMs])
        # first compute the nominal trajectory predicted by the ORM
        # before this point, the ORM has been calculated around the working point of the correctors
        # corrector strengths are in mrad at this point and U/s/VT produce ORM with units mm / mrad
        try:
            # twiss in values for the LTB
            # sigmaMat = at.sigma_matrix(betax = 3.731, betay = 2.128, alphax = -.0547, alphay = -.1263, emitx = 2.6e-7, emity = 2.6e-7, blength = 0, espread = 1.5e-2)
            # twiss in values for the BTS
            sigmaMat = at.sigma_matrix(betax = 12.13, betay = 2.94, alphax = -2.92, alphay = .75, emitx = 2.6e-7, emity = 2.6e-7, blength = 0, espread = 1.5e-2)
            beam = at.beam(numParticles, sigmaMat)
            arr, idxs, inv = np.unique(np.array([b['index'] for b in self.BPMs]), return_index = True, return_inverse = True)
            # calculate the nominal trajectory through the lattice
            beamOut = lattice_pass(self.lattice, deepcopy(beam), nturns = 1, refpts = arr) # has shape 6 x numParticles x numRefpts x nturns
            # get horizontal BPM list idxs
            xIdxs = [idxs[inv[i]] for i, b in enumerate(self.BPMs) if b['alignment'] == 'Horizontal']
            yIdxs = [idxs[inv[i]] for i, b in enumerate(self.BPMs) if b['alignment'] == 'Vertical']
            # get horizontal centres
            xCentres = np.mean(beamOut[0, :, xIdxs, 0], 1) * 1e3 # convert back to mm at the end
            yCentres = np.mean(beamOut[2, :, yIdxs, 0], 1) * 1e3
            S = np.zeros((len(self.BPMs), len(self.correctors)))
            np.fill_diagonal(S, self.s) # modifies matrix in-place
            ORM = self.U @ S @ self.VT
            cVec = np.array([c['value'] - c['default'] for c in self.correctors])[:, None] # convert to column vector
            # We solve (and inverse of) dBPMx = ORM dtheta (BPMs orders, x then y, and within those bins, by index & same for correctors)
            # 1. calculate the predicted trajectory for the set corrector values
            dBPM = ORM @ cVec
            data[:, 1] = np.concatenate([xCentres, yCentres]) # tracking output
        except Exception as e:
            sharedMemory.close()
            error.set()
            return e