from ..utils.multiprocessing import *

class Action:
    '''Generic action, an object that can be called to perform something.'''
    def __init__(self):
        super().__init__()

    def Run(self, isOnline, *args):
        '''`online` = <True/False> determine which method is run.'''
        if isOnline:
            return self.RunOnline(*args)
        return self.RunOffline(*args)

    # to be overriden by child class
    def RunOnline(self, *args):
        return -1

    # to be overriden by child class
    def RunOffline(self, *args):
        return -1
    
    # to be overriden by child class
    def __getstate__(self):
        pass

    # to be overriden by child class
    def __setstate__(self, state):
        pass