import at
from at import lattice_pass
import numpy as np
import time
from copy import deepcopy
from PySide6.QtCore import QTimer
from ..action import Action
from ... import simulator
from ... import shared

class OrbitResponseAction(Action):
    '''Perform, manipulate and save orbit response measurements.'''
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
                for b in self.BPMs.values()
            ],
            'correctors': [
                { 
                    'index': c.settings['linkedElement'].Index,
                    'alignment': c.settings['alignment'],
                    'default': c.settings['components']['value']['default']
                }
                for c in self.correctors.values()
            ],
        }

    def __setstate__(self, state):
        # Restore the lattice and settings...
        self.lattice = state['lattice']
        self.BPMs = state['BPMs']
        self.correctors = state['correctors']
        from ... import simulator
        self.simulator = simulator.Simulator()    

    def CheckForValidInputs(self) -> bool:
        # Have both correctors AND BPMs been suppled?
        if len(self.BPMs) == 0:
            print('No BPMs supplied! Backing out.')
            shared.workspace.assistant.PushMessage('Orbit Response is missing BPMs', 'Error')
            return False
        if len(self.correctors) == 0:
            print('No Correctors supplied! Backing out.')
            shared.workspace.assistant.PushMessage('Orbit Response is missing correctors', 'Error')
            return False
        # Check whether all PVs have been linked to lattice elements.
        for c in self.correctors.values():
            if 'linkedElement' not in c.settings.keys():
                print(f'{c.settings['name']} is missing a linked element! Backing out.')
                shared.workspace.assistant.PushMessage('One or more correctors have not been linked to lattice elements. Setup a connection in the inspector.', 'Error')
                return False
        for b in self.BPMs.values():
            if 'linkedElement' not in b.settings.keys():
                print(f'{b.settings['name']} is missing a linked element! Backing out.')
                shared.workspace.assistant.PushMessage('One or more BPMs have not been linked to lattice elements. Setup a connection in the inspector.', 'Error')
                return False
        print('All correctors and BPMs are linked to lattice elements.')
        return True

    def Run(self, pause, stop, numSteps, stepKick, repeats, numParticles = 10000, getRawData = True):
        '''Calculates the orbit response of the model using PyAT simulations.\n
        Accepts `correctors` (list of PVs) and `BPMs` (list of BPMs).'''
        # Have both correctors AND BPMs been suppled?
        numBPMs = len(self.BPMs)
        numCorrectors = len(self.correctors)
        BPMIdxs = np.empty(numBPMs, dtype = np.uint32) # refpts needs to be uint32 ndarray for atpass to work.
        for _, b in enumerate(self.BPMs):
            BPMIdxs[_] = np.uint32(b['index'])
        BPMIdxs = np.sort(BPMIdxs) # PyAT will throw an error if refpts isn't sorted in ascending order.
        # wait time between BPM measurements.
        wait = .2
        rawData = np.empty((numBPMs, numCorrectors, numSteps, repeats))
        # target kicks
        offset = int(numSteps / 2)
        kicks = (np.arange(0, numSteps, 1) - offset) * stepKick * 1e-3 # convert to mrad
        # Define the sigma matrix and beam with n particles ------- will allow custom beam profiles in a future version.
        sigmaMat = at.sigma_matrix(betax = 3.731, betay = 2.128, alphax = -.0547, alphay = -.1263, emitx = 2.6e-7, emity = 2.6e-7, blength = 0, espread = 1.5e-2)
        beam = at.beam(numParticles, sigmaMat)
        totalSteps = numBPMs * numCorrectors * len(kicks) * repeats
        counter = 1
        for col, c in enumerate(self.correctors):
            idx = 1 if c['alignment'] == 'Vertical' else 0
            for _, k in enumerate(kicks):
                kickAngle = c['default'] + k
                # Should errors be applied to the value? ---- this will be added in a future version.
                self.lattice[c['index']].KickAngle[idx] = kickAngle
                for row, b in enumerate(self.BPMs):
                    for r in range(repeats):
                        if stop.is_set():
                            if getRawData:
                                return None
                            return None, None
                        beamOut = lattice_pass(self.lattice, deepcopy(beam), nturns = 1, refpts = BPMIdxs) # has shape 6 x numParticles x numRefpts x nturns
                        centre = np.mean(beamOut[0, :, row]) if b['alignment'] == 'Horizontal' else np.mean(beamOut[2, :, row])
                        rawData[row, col, _, r] = centre
                        print(f'On step {counter} / {totalSteps}')
                        while pause.is_set():
                            if stop.is_set():
                                if getRawData:
                                    return None
                                return None, None
                            time.sleep(.1)
                        counter += 1
                # BPMs in the model are markers so we have the full phase space information but PVs will typically be separated into BPM:X, BPM:Y
                self.lattice[c['index']].KickAngle[idx] = 0
        if getRawData:
            return rawData
        return self.Fit(rawData, kicks, numCorrectors, numBPMs)

    def Fit(self, rawData, kicks, numCorrectors, numBPMs):
        '''Generates an Orbit Response Matrix using polyfit.'''
        data = rawData.mean(axis = 3)
        ORM = np.empty((numBPMs, numCorrectors))
        for col in range(numCorrectors):
            for row in range(numBPMs):
                y = data[row, col, :]
                m, C = np.polyfit(kicks, y, deg = 1, cov = True)
                ORM[row, col] = m[0]
        return rawData, ORM