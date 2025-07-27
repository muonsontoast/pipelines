import at
from at import atpass, lattice_pass
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
        # Step range in Amps / convert to mrad with factor 0.6 mrad / Amp
        # This is how you extract lattice elements by name
        # BPMs = shared.lattice.get_uint32_index('BPM')
        # Get a copy of the shared lattice to play with.
        self.lattice = deepcopy(shared.lattice)
        # Instantiate a simulator.
        self.simulator = simulator.Simulator()

    def RunOffline(self, correctors, BPMs, numSteps, stepKick, repeats, numParticles = 10000):
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
        BPMIdxs = np.empty(numBPMs, dtype = np.uint32) # refpts needs to be uint32 ndarray for atpass to work.
        for _, b in enumerate(BPMs):
            if 'linkedElement' not in b.settings.keys():
                print(f'{b.settings['name']} is missing a linked element! Backing out.')
                return
            BPMIdxs[_] = np.uint32(b.settings['linkedElement'].Index)
        print('All correctors and BPMs are linked to lattice elements.')
        # Follow the format of varying correctors, and then measuring response from the BPMs.
        # If non-zero error components are present, they will be applied to the correctors and/or BPMs.
        print('Copying lattice')
        lattice = deepcopy(shared.lattice)
        # wait time between BPM measurements.
        wait = .2
        rawData = np.empty((numBPMs, numCorrectors, repeats))
        # target kicks
        targets = np.arange(0, numSteps, 1)
        print('Setting correctors and measuring BPM responses.')
        # Define the sigma matrix and beam with n particles ------- will allow custom beam profiles in a future version.
        sigmaMat = at.sigma_matrix(betax = 3.731, betay = 2.128, alphax = -.0547, alphay = -.1263, emitx = 2.6e-7, emity = 2.6e-7, blength = 0, espread = 1.5e-2)
        beam = at.beam(numParticles, sigmaMat)
        for col, c in enumerate(correctors):
            # Set the corrector and collect the raw data.
            # No need to compensate for hysteresis in the offline model.
            # Check alignment
            idx = 1 if c.settings['alignment'] == 'Vertical' else 0
            kickAngle = c.settings['components']['value']['value']
            # Should errors be applied to the value? ---- this will be added in a future version.
            lattice[c.settings['linkedElement'].Index].KickAngle[idx] = kickAngle
            # Run the beam through the lattice and record positions on the BPMs
            beamOut = lattice_pass(self.lattice, beam, nturns = 1, refpts = BPMIdxs) # has shape 6 x numParticles x numRefpts x nturns
            # Calculate the beam centroid (since this is the only thing a BPM would return in the real machine).
            # Repeats will be added soon ...
            for _, b in enumerate(BPMs):
                centre = np.mean(beamOut[0, :, _]) if b.settings['alignment'] == 'Horizontal' else np.mean(beamOut[2, :, _])
                rawData[_, col, 0] = centre
                # time.sleep(5) # will be removed, here for testing ...
            # BPMs in the model are markers so we have the full phase space information but PVs will typically be separated into BPM:X, BPM:Y
            # iteration end - reset the PV
            lattice[c.settings['linkedElement'].Index].KickAngle[idx] = 0
        print('Finished orbit response measurement.')
        return rawData

