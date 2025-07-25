import at
import numpy as np
from copy import deepcopy
import time
from .. import simulator
from .. import shared

class OrbitResponseAction:
    '''Perform, manipulate and save orbit response measurements.'''
    '''
    Orbit response needs:
    1. Correctors
    2. BPMs
    3. Number of kicks
    4. Kick range (+- .5A / +- 1A, ...)
    5. Wait time - for online
    '''
    def __init__(self, hstrDict = dict(), vstrDict = dict()):
        print('Instantiating Orbit Response Action')
        # Step range in Amps / convert to mrad with factor 0.6 mrad / Amp
        stepRange = [-1, 1]
        numSteps = 5
        steps = np.linspace(stepRange[0], stepRange[1], numSteps)
        numRepeats = 4
        # This is how you extract lattice elements by name
        # BPMs = shared.lattice.get_uint32_index('BPM')

        self.simulator = simulator.Simulator()

    def RunOffline(self, correctors, BPMs, numSteps, stepKick, repeats):
        '''Calculates the orbit response of the model using PyAT simulations.\n
        Accepts `correctors` (list of PVs) and `BPMs` (list of BPMs).'''
        # Have both correctors AND BPMs been suppled?
        numBPMs = len(BPMs)
        if numBPMs == 0:
            print('No BPMs supplied! Backing out.')
            return
        numCorrectors = len(correctors)
        if numCorrectors == 0:
            print('No Correctors supplied! Backing out.')
            return
        # Check whether all PVs have been linked to lattice elements.
        for c in correctors:
            if 'linkedElement' not in c.settings.keys():
                print(f'{c.settings['name']} is missing a linked element! Backing out.')
                return
        for b in BPMs:
            if 'linkedElement' not in b.settings.keys():
                print(f'{b.settings['name']} is missing a linked element! Backing out.')
                return
        print('All correctors and BPMs are linked to lattice elements.')
        # Follow the format of varying correctors, and then measuring response from the BPMs.
        # If non-zero error components are present, they will be applied to the correctors and/or BPMs.
        print('Copying lattice')
        lattice = deepcopy(shared.lattice)
        # wait time between BPM measurements.
        wait = .2
        rawData = np.array((numBPMs, numCorrectors, repeats))
        # target kicks
        targets = np.arange(0, numSteps, 1)
        print('Setting correctors and measuring BPM responses.')
        for c in correctors:
            # Set the corrector and collect the raw data.
            # No need to compensate for hysteresis in the offline model.
            # Check alignment
            idx = 1 if c.settings['alignment'] == 'Vertical' else 0
            lattice[c.settings['linkedElement'].Index].KickAngle[idx] = c.settings['components']['value']['value']