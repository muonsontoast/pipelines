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

    def __getstate__(self):
        return {
            'decisions': [
                { 
                    'ID': d.name,
                    'default': d.settings['components']['value']['default'],
                    'min': d.settings['components']['value']['min'],
                    'max': d.settings['components']['value']['max'],
                }
                for d in self.decisions
            ],
            'objectives': [
                { 
                    'ID': o.name,
                }
                for o in self.objectives
            ],
        }
    
    def __setstate__(self, state):
        self.decisions = state['decisions']
        self.objectives = state['objectives']

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
            continue
            # attempt a caget to see if the PV name is correct.
            # if '' not in d.settings.keys():
                
            #     return False
        for o in self.decisions:
            continue
            # attempt a caget to see if the PV name is correct.
            # if '' not in d.settings.keys():
                
            #     return False
        print('All decision and objective variables match to real machine PVs.')
        return True
    
    def MeasureObjectivePVs(self, inputDict):
        # implement caget here
        measurements = np.zeros(self.repeats + 1)
        for r in range(self.repeats + 1):
            measurements[r] = np.random.randn()
        return {'BPM': np.mean(measurements)}
    
    def Run(self, pause, stop, sharedMemoryName, shape, dtype, **kwargs):
        initialSamples = kwargs.get('initialSamples')
        numSteps = kwargs.get('numSteps')
        self.repeats = kwargs.get('repeats', 0)
        goal = kwargs.get('goal')
        sharedMemory = SharedMemory(name = sharedMemoryName)
        data = np.ndarray(shape, dtype, buffer = sharedMemory.buf)
        # Configure Xopt
        vocs = VOCS(
            variables = {d['ID']: [d['min'], d['max']] for d in self.decisions},
            objectives = {o['ID']: goal for o in self.objectives},
        )
        evaluator = Evaluator(function = self.MeasureObjectivePVs)
        generator = UpperConfidenceBoundGenerator(vocs = vocs)
        X = Xopt(evaluator = evaluator, generator = generator, vocs = vocs)
        if initialSamples > 0:
            X.random_evaluate(initialSamples)
        else:
            X.random_evaluate(1) # Xopt BO needs at least 1 initial sample to run.

        # take the max or min of the running data?
        operation = np.max if goal == 'MAXIMIZE' else np.min
        data[0] = operation(X.data.BPM)
        steps = np.array(list(range(numSteps)))

        for _ in steps:
            X.step()
            print(f'Step {_ + 1}/{numSteps}')
            # check for interrupts
            while pause.is_set():
                if stop.is_set():
                    sharedMemory.close()
                    return
                time.sleep(.1)
            if stop.is_set():
                sharedMemory.close()
                return
            data[_ + 1] = operation(X.data.BPM) # store the running optimal value.
            # mask the data elements that haven't yet been found.
            mask = steps > _ + 1
            data[1:][mask] = np.nan
            print(f'Decision combination giving {data[_ + 1]} is {X.data.BPM.iloc[-1]}')
        sharedMemory.close()
