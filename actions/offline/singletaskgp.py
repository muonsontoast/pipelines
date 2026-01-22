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
            'online': self.parent.online,
        }

    def __setstate__(self, state):
        self.lattice = state['lattice']
        self.online:bool = state['online']
        self.simulator = Simulator(lattice = self.lattice)
    
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

    def Run(self, pause, stop, error, sharedMemoryName, shape, dtype, **kwargs):
        try: # make sure the process is guaranteed to exit
            numRepeats = 10
            numSamples = kwargs.get('numSamples')
            numParticles = kwargs.get('numParticles')
            numSteps = kwargs.get('numSteps')

            self.simulator.numParticles = numParticles
            sharedMemory = SharedMemory(name = sharedMemoryName)
            data = np.ndarray(shape, dtype, buffer = sharedMemory.buf)

            # how to construct Xopt optimiser inside this action? - don't, make this the evaluation inside the Single Task block.

            trackingData, _ = self.simulator.TrackBeam(numParticles)
            print(f'Here is the shape of the tracking data: {data.shape}')

            np.copyto(data, trackingData)

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
            sharedMemory.close()
            sharedMemory.unlink()
        except:
            sharedMemory.close()
            sharedMemory.unlink()