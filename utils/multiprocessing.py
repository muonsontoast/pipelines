import gc # garbage collection
import sys
# from multiprocessing import Queue, Process, Event, Value
# from threading import Event
import multiprocessing as mp
from multiprocessing import Process, Event
# from threading import Thread
mp.set_start_method('spawn', force = True) # force linux machines to call __getstate__ and __setstate__ methods attached to actions.
import time
from .. import shared

# Dict of running actions -- key is the parent entity ID, value is list where idx 0 is pause event and index 1 is stop event.
runningActions = dict()
workers = dict()

# Max wait time for save before main thread override
maxWait = .25 # in seconds

def SetGlobalToggleState():
    # change global toggle state if all runnable blocks share the same state
    myPauseState = runningActions[next(iter(runningActions.keys()))][0].is_set()
    for ID in shared.runnableBlocks:
        if ID in runningActions and runningActions[ID][0].is_set() != myPauseState:
            return
    shared.changeToggleState = False
    shared.toggleState = myPauseState

def TogglePause(entity, changeGlobalToggleState = True):
    runningActions[entity.ID][0].clear() if runningActions[entity.ID][0].is_set() else runningActions[entity.ID][0].set()
    if not changeGlobalToggleState:
        return
    SetGlobalToggleState()

def StopAction(entity, restart = False):
    '''Stop an entity's action if it is running. Returns true if successful else false.'''
    if entity.ID in runningActions:
        with entity.lock:
            runningActions[entity.ID][1].set()
            if restart:
                entity.resetApplied.set()
            entity.actionFinished.set()
        entity.title.setText(entity.name)
        gc.collect()
        return True
    else:
        return False

def StopActions():
    '''Stop all currently running actions.'''
    IDs = list(runningActions.keys())
    for ID in IDs:
        runningActions[ID][1].set()

def PersistentWorker(pause, stop, error, sharedMemoryName, shape, action, pipe, **kwargs):
    while True:
        params = pipe.recv()
        if params is None:
            break
        result = action(pause, stop, error, sharedMemoryName, shape, params, **kwargs)
        pipe.send(result)
    pipe.close()
    sys.exit(0)

def CreatePersistentWorker(entity, emptyArray, inQueue, outQueue, action, **kwargs):
    '''`signals` should be a dict of QtCore Signals.'''
    ctx = mp.get_context('spawn')
    outPipe, inPipe = ctx.Pipe()
    entity.CreateEmptySharedData(emptyArray)
    Process(target = PersistentWorker, args = (*runningActions[entity.ID][:-1], entity.dataSharedMemory.name, emptyArray.shape, action, inPipe), kwargs = kwargs).start()
    while True:
        params = inQueue.get()
        outPipe.send(params)
        if params is None:
            break
        result = outPipe.recv()
        outQueue.put(result)
        runningActions[entity.ID][-1] += 1
    outPipe.close()
    runningActions.pop(entity.ID)