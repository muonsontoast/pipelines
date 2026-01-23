import time
import numpy as np
from multiprocessing.shared_memory import SharedMemory
from ..action import Action
from ...simulator import Simulator
from ... import shared

class SingleTaskGPAction(Action):
    def __init__(self, parent):
        '''Accepts a `parent` block.'''
        super().__init__(parent)

    def __getstate__(self):
        return {
            'lattice': shared.lattice,
            'decisions': [
                {
                    'name': d.settings['linkedElement'].Name,
                    'index': d.settings['linkedElement'].Index,
                    's': d.settings['linkedElement']['s (m)'],
                    'set': d.settings['components']['value']['value'],
                }
                for d in self.parent.decisions
            ],
            'objectives': [
                {
                    'name': o.settings['linkedElement'].Name,
                    'index': o.settings['linkedElement'].Index,
                    's': o.settings['linkedElement']['s (m)'],
                    'dtype': o.settings['dtype'],
                }
                for o in self.parent.objectives
            ],
        }

    def __setstate__(self, state):
        self.lattice = state['lattice']
        self.simulator = Simulator(lattice = self.lattice)
        self.decisions:list = state['decisions']
        self.objectives:list = state['objectives']
        self.numObjectives:int = len(state['objectives'])
        self.sharedMemoryCreated = False
        self.computations = {
            'CHARGE': self.GetCharge,
            'X': self.GetX,
            'Y': self.GetY,
            'XP': self.GetXP,
            'YP': self.GetYP,
        }
    
    def CheckForValidInputs(self):
        # Have both correctors AND BPMs been suppled?
        if len(self.parent.decisions) == 0:
            print('Single Task GP is missing decision variables.')
            shared.workspace.assistant.PushMessage('Single Task GP is missing decision variables.', 'Error')
            return False
        if len(self.parent.objectives) == 0:
            print('Single Task GP is missing objectives.')
            shared.workspace.assistant.PushMessage('Single Task GP is missing objectives.', 'Error')
            return False
        # Check whether all PVs have been linked to lattice elements.
        for d in self.parent.decisions:
            if d.type == 'SVD':
                if np.isinf(shared.entities[d.ID].streams[self.parent.streamTypesIn[d.ID]]()['data']).any():
                    print(f'{d.settings['name']} is missing an SVD! Backing out.')
                    shared.workspace.assistant.PushMessage('SVD needs to be run on an ORM first.', 'Error')
                    return False
            elif 'linkedElement' not in d.settings.keys():
                print(f'{d.settings['name']} is missing a linked element! Backing out.')
                shared.workspace.assistant.PushMessage('One or more decision variables have not been linked to lattice elements. Setup a connection in the inspector.', 'Error')
                return False
        for o in self.parent.objectives:
            if o.type in ['Add', 'Subtract']:
                if o.A is None or o.B is None:
                    print(f'{o.name} is missing operands! Backing out.')
                    shared.workspace.assistant.PushMessage(f'{o.name} is missing operands.', 'Error')
                    return False
            elif 'linkedElement' not in o.settings.keys():
                print(f'{o.settings['name']} is missing a linked element! Backing out.')
                shared.workspace.assistant.PushMessage('One or more objectives have not been linked to lattice elements. Setup a connection in the inspector.', 'Error')
                return False
        print('All decision variables and objectives are linked to lattice elements.')
        return True
    
    def GetCharge(self, tracking, index):
        '''Returns charge at an element in units of fundamental charge, q.'''
        return np.sum(np.where(np.any(np.isnan(tracking[:, :, index, 0]), axis = 0), False, True))

    def GetX(self, tracking, index):
        '''Returns the centroid of the beam in the horizontal axis at an element.'''
        return np.nanmean(tracking[0, :, index, 0])

    def GetY(self, tracking, index):
        '''Returns the centroid of the beam in the vertical axis at an element.'''
        return np.nanmean(tracking[2, :, index, 0])

    def GetXP(self, tracking, index):
        '''Returns the horizontal momentum of the beam at an element.'''
        return np.nanmean(tracking[1, :, index, 0])

    def GetYP(self, tracking, index):
        '''Returns the vertical momentum of the beam at an element.'''
        return np.nanmean(tracking[3, :, index, 0])

    def Run(self, pause, stop, error, progress, sharedMemoryName, shape, dtype, **kwargs):
        
        '''Action does this:
            1. Track Beam
            2. Store objectives vector in data
            3. Return
        '''

        # numRepeats = kwargs.get('numRepeats')
        numRepeats = 1
        numParticles = kwargs.get('numParticles')
        totalSteps = kwargs.get('totalSteps')
        stepOffset = kwargs.get('stepOffset', 0)
        self.simulator.numParticles = numParticles
        
        if not self.sharedMemoryCreated:
            sharedMemory = SharedMemory(name = sharedMemoryName)
            data = np.ndarray(shape, dtype, buffer = sharedMemory.buf)
            data[:] = np.inf
            self.sharedMemoryCreated = True
        
        result = np.zeros(numRepeats, self.numObjectives)

        try:
            for r in range(numRepeats):
                tracking, _ = self.simulator.TrackBeam(numParticles)
                for it, o in enumerate(self.objectives):
                    result[r, it] = self.computations[o['dtype']](tracking, o['index'])
                    # extract the relevant objective information
                    # check for interrupts
                    while pause.is_set():
                        if stop.is_set():
                            sharedMemory.close()
                            sharedMemory.unlink()
                            return
                        time.sleep(.1)
                    if stop.is_set():
                        sharedMemory.close()
                        sharedMemory.unlink()
                        return
                progress.value = (r + 1 + stepOffset) / totalSteps
            # return the average over repeats as an array of length len(self.objectives)
            np.copyto(data, np.mean(result, axis = 0))
        except Exception as e:
            print(e)
        stop.set()