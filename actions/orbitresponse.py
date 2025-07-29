import at
from at import lattice_pass
import numpy as np
from copy import deepcopy
from .action import Action
from .. import simulator
from .. import shared

class OrbitResponseAction(Action):
    '''Perform, manipulate and save orbit response measurements.'''
    '''
    Orbit response needs:
    1. Correctors
    2. BPMs
    3. Number of kicks
    4. Kick range (+- .5A / +- 1A, ...)
    5. Wait time - for online
    '''
    def __init__(self):
        super().__init__()
        # Step range in Amps / convert to mrad with factor 0.6 mrad / Amp
        # This is how you extract lattice elements by name
        # BPMs = shared.lattice.get_uint32_index('BPM')
        self.correctors = None
        self.BPMs = None
        # Get a copy of the shared lattice to play with.
        self.lattice = deepcopy(shared.lattice)
        # Instantiate a simulator.
        self.simulator = simulator.Simulator()

    def __getstate__(self):
        # Only pickle the lattice and the minimal settings lists.
        return {
            'lattice': self.lattice,
            'BPMs': [
                { 
                    'index': b.settings['linkedElement'].Index,
                    'alignment': b.settings['alignment'] 
                }
                for b in self.BPMs
            ],
            'correctors': [
                { 
                    'index': c.settings['linkedElement'].Index,
                    'alignment': c.settings['alignment'],
                    'default': c.settings['components']['value']['default']
                }
                for c in self.correctors
            ],
        }

    def __setstate__(self, state):
        # Restore the lattice and settings...
        self.lattice = state['lattice']
        self.BPMs = state['BPMs']
        self.correctors = state['correctors']
        # **Re‑create** a fresh simulator in the child
        from .. import simulator
        self.simulator = simulator.Simulator()    

    def CheckForValidInputs(self) -> bool:
        # Have both correctors AND BPMs been suppled?
        if len(self.BPMs) == 0:
            print('No BPMs supplied! Backing out.')
            return False
        if len(self.correctors) == 0:
            print('No Correctors supplied! Backing out.')
            return False
        # Check whether all PVs have been linked to lattice elements.
        for c in self.correctors:
            if 'linkedElement' not in c.settings.keys():
                print(f'{c.settings['name']} is missing a linked element! Backing out.')
                return False
        for _, b in enumerate(self.BPMs):
            if 'linkedElement' not in b.settings.keys():
                print(f'{b.settings['name']} is missing a linked element! Backing out.')
                return False
        print('All correctors and BPMs are linked to lattice elements.')
        return True

    def RunOffline(self, numSteps, stepKick, repeats, numParticles = 10000):
        '''Calculates the orbit response of the model using PyAT simulations.\n
        Accepts `correctors` (list of PVs) and `BPMs` (list of BPMs).'''
        # Have both correctors AND BPMs been suppled?
        numBPMs = len(self.BPMs)
        numCorrectors = len(self.correctors)
        BPMIdxs = np.empty(numBPMs, dtype = np.uint32) # refpts needs to be uint32 ndarray for atpass to work.
        for _, b in enumerate(self.BPMs):
            BPMIdxs[_] = np.uint32(b['index'])
        # Follow the format of varying correctors, and then measuring response from the BPMs.
        # If non-zero error components are present, they will be applied to the correctors and/or BPMs.
        # wait time between BPM measurements.
        wait = .2
        rawData = np.empty((numBPMs, numCorrectors, repeats + 1))
        # target kicks
        offset = int(numSteps / 2) + 1
        kicks = (np.arange(0, numSteps + .1, 1) - offset) * stepKick * 1e-3 # convert to mrad
        # Define the sigma matrix and beam with n particles ------- will allow custom beam profiles in a future version.
        sigmaMat = at.sigma_matrix(betax = 3.731, betay = 2.128, alphax = -.0547, alphay = -.1263, emitx = 2.6e-7, emity = 2.6e-7, blength = 0, espread = 1.5e-2)
        beam = at.beam(numParticles, sigmaMat)
        for col, c in enumerate(self.correctors):
            idx = 1 if c['alignment'] == 'Vertical' else 0
            for k in kicks:
                kickAngle = c['default'] + k
                # Should errors be applied to the value? ---- this will be added in a future version.
                self.lattice[c['index']].KickAngle[idx] = kickAngle
                for row, b in enumerate(self.BPMs):
                    for r in range(repeats + 1):
                        beamOut = lattice_pass(self.lattice, beam, nturns = 1, refpts = BPMIdxs) # has shape 6 x numParticles x numRefpts x nturns
                        centre = np.mean(beamOut[0, :, _]) if b['alignment'] == 'Horizontal' else np.mean(beamOut[2, :, _])
                        rawData[row, col, r] = centre
                # BPMs in the model are markers so we have the full phase space information but PVs will typically be separated into BPM:X, BPM:Y
                self.lattice[c['index']].KickAngle[idx] = 0
        return rawData

