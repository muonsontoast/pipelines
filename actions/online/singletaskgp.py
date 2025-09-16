import numpy as np
from multiprocessing.shared_memory import SharedMemory
from ..action import Action
from ...utils import cothread
from ... import shared

class SingleTaskGPAction(Action):
    def __init__(self, parent):
        '''Accepts a `parent` block.'''
        super().__init__(parent)

    def CheckForValidInputs(self):
        print('Online GP action is checking for valid inputs!')
        if len(self.parent.decisions) == 0:
            shared.workspace.assistant.PushMessage('Single Task GP is missing decision variables.', 'Error')
            return False
        if len(self.parent.objectives) == 0:
            shared.workspace.assistant.PushMessage('Single Task GP is missing objectives.', 'Error')
            return False
        # Attempt a caget on the decision variables to see if they are valid
        try:
            for d in self.decisions:
                cothread.caget(d.name)
            print('All online GP inputs exist on the machine!')
        except Exception as e:
            shared.workspace.assistant.PushMessage(f'{e}.', 'Error')
            return False
        
        return True