import at
import numpy as np
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
        print('=== ORM ===')
        # Get the indices of correctors in the lattice
        # idxs = at.get_uint32_index(shared.lattice, at.Corrector)
        # Step range in Amps / convert to mrad with factor 0.6 mrad / Amp
        stepRange = [-1, 1]
        numSteps = 5
        steps = np.linspace(stepRange[0], stepRange[1], numSteps)
        numRepeats = 4
        # References to correctors
        HSTRIdxs = shared.lattice.get_uint32_index('HSTR')
        VSTRIdxs = shared.lattice.get_uint32_index('VSTR')
        BPMs = shared.lattice.get_uint32_index('BPM')
        ORM = np.empty(len(HSTRIdxs) + len(VSTRIdxs), len(BPMs))

        sim = simulator.Simulator()
        # 1. Set the corrector strengths to nominal
        
        # 2. Iterate over correctors
        # for _ in range(len(HSTRIdxs)):
        #     v = 0
        #     for r in range(numRepeats):
        #         # measure orbit response
        #         # caget('BPM')
        #         v += sim.