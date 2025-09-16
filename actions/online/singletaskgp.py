import numpy as np
from multiprocessing.shared_memory import SharedMemory
from ..action import Action
from ... import shared

class SingleTaskGPAction(Action):
    def __init__(self, parent):
        '''Accepts a `parent` block.'''
        super().__init__(parent)

    def CheckForValidInputs(self):
        if len(self.parent.decisions) == 0:
            shared.workspace.assistant.PushMessage('Single Task GP is missing decision variables.', 'Error')
            return False
        if len(self.parent.objectives) == 0:
            shared.workspace.assistant.PushMessage('Single Task GP is missing objectives.', 'Error')
            return False
        # Attempt a caget on the decision variables to see if they are valid