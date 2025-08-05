from xopt.vocs import VOCS
from xopt.evaluator import Evaluator
from xopt.generators.bayesian import UpperConfidenceBoundGenerator
from xopt import Xopt
import math
import time
import numpy as np
from multiprocessing.shared_memory import SharedMemory
from ..action import Action
from ... import shared

class SingleTaskGPAction(Action):
    def __init__(self):
        super().__init__()
        self.decisions = None
        self.objectives = None
        self.constraints = None

    def Sin(self, inputDict):
        return {'f': math.sin(inputDict['x']) * math.cos(inputDict['x']) * math.sin(3 * inputDict['x']) * math.sin(math.sinh(inputDict['x']))}

    def __getstate__(self):
        return {
            'lattice': self.lattice,
            'decisions': [
                { 
                    'index': d.settings['linkedElement'].Index,
                    'alignment': d.settings['alignment'] 
                }
                for d in self.decisions
            ],
            'objectives': [
                { 
                    'index': o.settings['linkedElement'].Index,
                    'alignment': o.settings['alignment'],
                }
                for o in self.objectives
            ],
        }
    
    def CheckForValidInputs(self):
        # Have both correctors AND BPMs been suppled?
        if len(self.decisions) == 0:
            print('No decision variables supplied! Backing out.')
            shared.workspace.assistant.PushMessage('Single Task GP is missing decision variables', 'Error')
            return False
        if len(self.objectives) == 0:
            print('No objective variables supplied! Backing out.')
            shared.workspace.assistant.PushMessage('Single Task GP is missing objectives', 'Error')
            return False
        # Check whether all PVs have been linked to lattice elements.
        for d in self.decisions:
            if 'linkedElement' not in d.settings.keys():
                print(f'{d.settings['name']} is missing a linked element! Backing out.')
                shared.workspace.assistant.PushMessage('One or more decision variables have not been linked to lattice elements. Setup a connection in the inspector.', 'Error')
                return False
        for o in self.objectives:
            if 'linkedElement' not in o.settings.keys():
                print(f'{o.settings['name']} is missing a linked element! Backing out.')
                shared.workspace.assistant.PushMessage('One or more objectives have not been linked to lattice elements. Setup a connection in the inspector.', 'Error')
                return False
        print('All decision variables and objectives are linked to lattice elements.')
        return True

    def Run(self, pause, stop, sharedMemoryName, shape, dtype, getRawData: bool = True, **kwargs):
        initialSamples = kwargs.get('initialSamples')
        numSteps = kwargs.get('numSteps')
        repeats = kwargs.get('repeats')
        numParticles = kwargs.get('numParticles', 10000)
        sharedMemory = SharedMemory(name = sharedMemoryName)
        data = np.ndarray(shape, dtype, buffer = sharedMemory.buf)
        vocs = VOCS(
            variables = {'x': [0, 2 * math.pi]},
            objectives = {'f': 'MINIMIZE'},
        )
        evaluator = Evaluator(function = self.Sin)
        generator = UpperConfidenceBoundGenerator(vocs = vocs)
        X = Xopt(evaluator = evaluator, generator = generator, vocs = vocs)
        if initialSamples > 0:
            X.random_evaluate(initialSamples)
        else:
            X.random_evaluate(1) # Xopt BO needs at least 1 initial sample to run.

        data[0] = np.min(X.data.f)

        for _ in range(numSteps):
            X.step()
            print(f'Hi! step {_ + 1}/{numSteps}')
            # check for interrupts
            while pause.is_set():
                if stop.is_set():
                    sharedMemory.close()
                    return
                time.sleep(.1)
            if stop.is_set():
                sharedMemory.close()
                return
            data[_ + 1] = np.min(X.data.f) # store the running optimal value.
        sharedMemory.close()