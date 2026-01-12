from PySide6.QtCore import QTimer
from copy import deepcopy
from ..utils.multiprocessing import *
from ..simulator import Simulator

class Action:
    '''Generic action, an object that can be called to perform something.'''
    # action block types - these trigger shared memory creation by downstream blocks when propagating up the heirarchy
    actionBlockTypes = ['Single Task GP', 'ORM', 'SVD']
    
    def __init__(self, parent, pollUpstreamRate = 5):
        super().__init__()
        # Get a copy of the shared lattice to play with.
        self.lattice = deepcopy(shared.lattice)
        # Instantiate a simulator.
        self.simulator = Simulator()
        self.pollUpstreamRate = pollUpstreamRate
        self.timeBetweenPolls = 1 / pollUpstreamRate * 1e3 # in ms
        self.dependentsResult:list = [] # store the data from reading dependents
        self.resultsWritten:bool = False
        self.independentsSet:bool = False
        self.parent = parent
    
    # to be overriden by child class
    def __getstate__(self):
        pass

    # to be overriden by child class
    def __setstate__(self, state):
        pass

    def SetIndependents(self, independents:dict, targets:dict):
        '''Sets all independent input variables to the block before performing an action and waits for them to finish.\n
        `independents` is a dict of streams generated from incoming decision variables of the form { ID: stream }.\n
        `targets` is a dict with setpoints for the independents, of the form { \'ID\': **int/float**, ... }\n
        if `online` is True, PV names are used instead of linked idxs.'''
        self.resultsWritten = False
        for ID, stream in independents.items():
            print(f'Setting {shared.entities[ID].name}')
            # each row in a data is considered as another input
            setpoints = (np.array([targets[f'{ID}-{dim}'] for dim in range(stream['data'].shape[0])]) @ stream['data'])
            lims = np.array(list(stream['lims'].values())) if type(stream['lims']) == dict else np.array([stream['lims']])
            rng = lims[:, 1] - lims[:, 0]
            # transform the setpoints to respect the limits of the decision variables
            setpoints = lims[:, 0] + rng * .5 * (1 + np.tanh(setpoints))
            shared.entities[ID].Start(setpoints = setpoints)
        
        def WaitUntilInputsSet():
            for stream in independents.values():
                if np.isinf(stream['data']).any():
                    return QTimer.singleShot(self.timeBetweenPolls, WaitUntilInputsSet)
            self.resultsWritten = True
        WaitUntilInputsSet()

    async def ReadDependents(self, dependents:list[dict], actionData:np.ndarray = np.array([])) -> np.ndarray:
        '''Records the values of incoming outputs linked to the block and waits for them to finish.\n
        `dependents` is a list of dicts generated during pickling of block data by the action, of the form [ { \'ID\': **ID**, \'stream\': **stream** }, ... ]\n
        `actionData` is a numpy array holding data generated after running the action, from which the objectives can be extracted.'''

        self.resultsWritten = False
        for d in dependents:
            await shared.entities[d['ID']].Start(downstreamData = actionData) # blindly start all inputs for now ...

        # wait for dependents that have been run to finish -- needs more work to be error aware
        def CheckDependentsRunning():
            for d in dependents:
                if np.isnan(shared.entities[d['ID']].data[1]).any():
                    return QTimer.singleShot(self.timeBetweenPolls, CheckDependentsRunning)
                # if np.isinf(shared.entities[d['ID']].streams[d['stream']]()['data']).any():
                #     return QTimer.singleShot(self.timeBetweenPolls, CheckDependentsRunning)
            self.resultsWritten = True
        CheckDependentsRunning()
        print(f'{self.parent.name} is done running dependents!')

    def UpdateLinkedElement(self, elementInfo:dict, value:float):
        '''`elementInfo` is a dict containing a linked index `linkedIdx` and any other information relevant to the update.'''
        linkedType = type(self.lattice[elementInfo['linkedIdx']]).__name__
        if linkedType == 'Corrector':
            idx = 0 if elementInfo['alignment'] == 'Horizontal' else 1
            self.lattice[elementInfo['linkedIdx']].KickAngle[idx] = value * 1e-3 # mrad -> rad
        elif linkedType == 'Quadrupole':
            self.lattice[elementInfo['linkedIdx']].K = value