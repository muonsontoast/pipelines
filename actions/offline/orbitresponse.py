import at
from at import lattice_pass
import numpy as np
import time
from copy import deepcopy
from multiprocessing.shared_memory import SharedMemory
from ..action import Action
from ...simulator import Simulator
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

    def __getstate__(self):
        print('Inside ORM action getter, correctors look like:')
        print([v.name for v in self.correctors.values()])
        return {
            'lattice': self.lattice,
            'BPMs': [
                { 
                    'name': b.name,
                    'index': b.settings['linkedElement'].Index,
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
                    'default': c.settings['components']['value']['default'],
                    'linkedElementAttrs': c.linkedElementAttrs,
                }
                for c in self.correctors.values()
            ],
        }

    def __setstate__(self, state):
        self.lattice = state['lattice']
        self.BPMs = state['BPMs']
        self.correctors = state['correctors']
        self.simulator = Simulator()    

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

    def Run(self, pause, stop, sharedMemoryName, shape, dtype, **kwargs):
        '''Calculates the orbit response of the model using PyAT simulations.\n
        Accepts `correctors` (list of PVs) and `BPMs` (list of BPMs).'''
        print('Inside ORM action, correctors look like:')
        print([v['name'] for v in self.correctors])
        numSteps = kwargs.get('numSteps')
        stepKick = kwargs.get('stepKick')
        repeats = kwargs.get('repeats')
        numParticles = kwargs.get('numParticles', 10000)
        sharedMemory = SharedMemory(name = sharedMemoryName)
        data = np.ndarray(shape, dtype, buffer = sharedMemory.buf)
        numBPMs = len(self.BPMs)
        numCorrectors = len(self.correctors)
        offset = int(numSteps / 2)
        kicks = (np.arange(0, numSteps, 1) - offset) * stepKick * 1e-3 # convert to mrad
        # twiss in values for the LTB
        # sigmaMat = at.sigma_matrix(betax = 3.731, betay = 2.128, alphax = -.0547, alphay = -.1263, emitx = 2.6e-7, emity = 2.6e-7, blength = 0, espread = 1.5e-2)
        # twiss in values for the BTS
        sigmaMat = at.sigma_matrix(betax = 12.13, betay = 2.94, alphax = -2.92, alphay = .75, emitx = 2.6e-7, emity = 2.6e-7, blength = 0, espread = 1.5e-2)
        beam = at.beam(numParticles, sigmaMat)
        counter = 0
        totalSteps = numCorrectors * numBPMs * numSteps * repeats
        # # Sort the correctors and BPMs to produce a proper ORM (Index -> Alignment)
        # self.correctors = sorted(sorted(self.correctors, key = lambda c: c['index']), key = lambda c: c['alignment'])
        # self.BPMs = sorted(sorted(self.BPMs, key = lambda b: b['index']), key = lambda b: b['alignment'])
        for col, c in enumerate(self.correctors):
            idx = 1 if c['alignment'] == 'Vertical' else 0
            for _, k in enumerate(kicks):
                kickAngle = c['default'] + k
                # Should errors be applied to the value? ---- this will be added in a future version.
                self.lattice[c['index']].KickAngle[idx] = kickAngle
                for row, b in enumerate(self.BPMs):
                    BPMIdx = b['index']
                    for r in range(repeats):
                        beamOut = lattice_pass(self.lattice, deepcopy(beam), nturns = 1, refpts = np.array([BPMIdx])) # has shape 6 x numParticles x numRefpts x nturns
                        centre = np.mean(beamOut[0, :, 0, 0]) if b['alignment'] == 'Horizontal' else np.mean(beamOut[2, :, 0, 0])
                        data[row, col, _, r] = centre
                        print(f'On step {counter} / {totalSteps}', end = '\r', flush = True)
                        counter += 1
                        # check for interrupts
                        while pause.is_set():
                            if stop.is_set():
                                sharedMemory.close()
                                return
                            time.sleep(.1)
                        if stop.is_set():
                            sharedMemory.close()
                            return
                # BPMs in the model are markers so we have the full phase space information but PVs will typically be separated into BPM:X, BPM:Y
                self.lattice[c['index']].KickAngle[idx] = 0
        self.Fit(data, kicks, numCorrectors, numBPMs,
            kwargs.get('postProcessedSharedMemoryName'),
            kwargs.get('postProcessedShape'),
            kwargs.get('postProcessedDType'),
        )
        sharedMemory.close() # remove this process' access to the shared data array.

    def Fit(self, data, kicks, numCorrectors, numBPMs, postProcessedSharedMemoryName, postProcessedShape, postProcessedDType):
        '''Generates an Orbit Response Matrix using polyfit.'''
        sharedMemory = SharedMemory(name = postProcessedSharedMemoryName)
        postProcessedData = np.ndarray(postProcessedShape, postProcessedDType, buffer = sharedMemory.buf)
        dataAveragedOverRepeats = data.mean(axis = 3)
        for col in range(numCorrectors):
            for row in range(numBPMs):
                y = dataAveragedOverRepeats[row, col, :]
                m, C = np.polyfit(kicks, y, deg = 1, cov = True)
                postProcessedData[row, col] = m[0]
        sharedMemory.close() # remove this process' access to the shared ORM array.