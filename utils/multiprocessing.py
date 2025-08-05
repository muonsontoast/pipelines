from multiprocessing import Queue, Process, Event
import multiprocessing as mp
mp.set_start_method('spawn', force = True) # force linux machines to call __getstate__ and __setstate__ methods attached to actions.
import threading
import numpy as np
from .entity import Entity
from .. import shared

# Dict of running actions -- key is the parent entity ID, value is list where idx 0 is pause event and index 1 is stop event.
runningActions = dict()

def TogglePause(entity, override = None):
    '''Pause the action of an entity if it is running one.'''
    if entity.ID not in runningActions:
        return
    if override:
        runningActions[entity.ID][0].set()
        state = False
    else:
        if override == False:
            runningActions[entity.ID][0].clear()
            state = True
        else:
            runningActions[entity.ID][0].set() if not runningActions[entity.ID][0].is_set() else runningActions[entity.ID][0].clear()
            state = False if runningActions[entity.ID][0].is_set() else True
    if not state:
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Paused)')
        entity.runningCircle.Stop()
    else:
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Running)')
        entity.runningCircle.Start()
    return state

def StopAction(entity):
    '''Stop an entity's action if it is running. Returns true if successful else false.'''
    if entity.ID in runningActions:
        runningActions[entity.ID][1].set()
        shared.entities[entity.ID].title.setText(f'{shared.entities[entity.ID].name.split(' (')[0]} (Empty)')
        shared.entities[entity.ID].runningCircle.Stop()
        return True
    else:
        print(f'{entity.name} has no running action to stop.')
        shared.workspace.assistant.PushMessage(f'{entity.name} is not running.', 'Error')
        return False

def StopActions():
    '''Stop all currently running actions.'''
    IDs = list(runningActions.keys())
    for ID in IDs:
        shared.entities[ID].title.setText(f'{shared.entities[ID].name.split(' (')[0]} (Empty)')
        shared.entities[ID].runningCircle.Stop()
        runningActions[ID][1].set()

def RunProcess(action, queue, pause, stop, sharedMemoryName, shape, dtype, **kwargs):
    '''Accepts an entity `ID`, and other `args` to pass to the Run() method of the entity's action.'''
    pause.clear()
    stop.clear()
    queue.put(action.Run(pause, stop, sharedMemoryName, shape, dtype, **kwargs))

def CheckProcess(entity, process: Process, queue: Queue, getRawData = True):
    if queue.empty():
        threading.Timer(.1, CheckProcess, args = (entity, process, queue, getRawData)).start()
        return
    process.join()
    runningActions.pop(entity.ID)
    entity.runningCircle.Stop()
    if entity.data.shape != ():
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Holding Data)')
        shared.workspace.assistant.PushMessage(f'{entity.name} has finished and is no longer running.')
    else:
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Empty)')
        shared.workspace.assistant.PushMessage('Stopped action(s).')

def PerformAction(entity: Entity, emptyDataArray: np.ndarray, **kwargs) -> bool:
    '''Set `getRawData` to False to perform post processing.\n
    Supply an `emptyDataArray` numpy array of the final shape.\n
    Supply an attribute name `postProcessedDataName` for the post processed data to be stored in.\n
    If post processing, also supply an `emptyPostProcessedDataArray` numpy array of the final shape.\n
    Returns True if successful else False.'''
    if entity.ID in runningActions:
        if runningActions[entity.ID][0].is_set():
            TogglePause(entity, False)
            return True
        else:
            return False
    kwargs['getRawData'] = kwargs.pop('getRawData', True)
    postProcessedDataName = kwargs.pop('postProcessedDataName', None)
    if postProcessedDataName:
        emptyPostProcessedDataArray = kwargs.pop('emptyPostProcessedDataArray', None)
        if emptyPostProcessedDataArray.shape != ():
            entity.CreateEmptySharedData(emptyPostProcessedDataArray, postProcessedDataName)
            # assign additional kwargs for post processing
            kwargs['postProcessedSharedMemoryName'] = getattr(entity, f'{postProcessedDataName}SharedMemory').name
            kwargs['postProcessedShape'] = emptyPostProcessedDataArray.shape
            kwargs['postProcessedDType'] = emptyPostProcessedDataArray.dtype
        else: # user has supplied a name for the post process but not an empty array, so raise an error.
            print('Post processing attribute name was supplied without also providing an empty numpy array!')
            return
    entity.CreateEmptySharedData(emptyDataArray) # share the data with the process.
    entity.data[:] = np.nan
        
    queue = Queue()
    action = entity.offlineAction if not entity.online else entity.onlineAction
    # Define the pause and stop events and add them to the runningActions dict.
    runningActions[entity.ID] = [Event(), Event()]

    process = Process(
        target = RunProcess,
        args = (action, queue, runningActions[entity.ID][0], runningActions[entity.ID][1], entity.dataSharedMemory.name, emptyDataArray.shape, emptyDataArray.dtype),
        kwargs = kwargs
    )
    entity.runningCircle.Start()
    entity.title.setText(f'{entity.name.split(' (')[0]} (Running)')
    process.start()
    # periodically check if the action has finished ...
    threading.Timer(.1, CheckProcess, args = (entity, process, queue, kwargs['getRawData'])).start()
    return True