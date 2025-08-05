import time
from ..utils.multiprocessing import *
from copy import deepcopy
from ..simulator import Simulator

class Action:
    '''Generic action, an object that can be called to perform something.'''
    def __init__(self):
        super().__init__()
        # Get a copy of the shared lattice to play with.
        self.lattice = deepcopy(shared.lattice)
        # Instantiate a simulator.
        self.simulator = Simulator()
    
    # to be overriden by child class
    def __getstate__(self):
        pass

    # to be overriden by child class
    def __setstate__(self, state):
        pass