import numpy as np
import aioca
from ..action import Action
from ... import shared

class SingleTaskGPAction(Action):
    def __init__(self, parent, timeout = 5):
        '''Accepts a `parent` block.'''
        super().__init__(parent)
        self.timeout = timeout
        self.decisions = None

    async def CheckForValidInputs(self):
        print('Online GP action is checking for valid inputs!')
        if len(self.parent.decisions) == 0:
            shared.workspace.assistant.PushMessage('Single Task GP is missing decision variables.', 'Error')
            return False
        if len(self.parent.objectives) == 0:
            shared.workspace.assistant.PushMessage('Single Task GP is missing objectives.', 'Error')
            return False
        # Attempt a caget on the decision variables to see if they are valid
        print('Checking all decision variables attached to this GP')
        try:
            for d in self.decisions:
                print(f'Checking {d.name}')
                await aioca.caget(d.name + ':I', timeout = self.timeout)
            print('All online GP inputs exist on the machine!')
        except Exception as e:
            print('Some decision vars were not valid')
            shared.workspace.assistant.PushMessage(f'{e}.', 'Error')
            return False
        
        return True