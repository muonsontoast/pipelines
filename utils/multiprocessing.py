from multiprocessing import Queue, Process, Event
import multiprocessing as mp
mp.set_start_method('spawn', force = True) # force linux machines to call __getstate__ and __setstate__ methods attached to actions.
import threading
import numpy as np
import time
from .entity import Entity
from .. import shared

# Dict of running actions -- key is the parent entity ID, value is list where idx 0 is pause event and index 1 is stop event.
runningActions = dict()

# Max wait time for save before main thread override
maxWait = .25 # in seconds

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
        entity.title.setText(f'{entity.name.split(' (')[0]} (Stopped)')
        entity.runningCircle.Stop()
        return True
    else:
        print(f'{entity.name} has no running action to stop.')
        shared.workspace.assistant.PushMessage(f'{entity.name} is not running.', 'Error')
        return False

def StopActions():
    '''Stop all currently running actions.'''
    IDs = list(runningActions.keys())
    for ID in IDs:
        shared.entities[ID].title.setText(f'{shared.entities[ID].name.split(' (')[0]} (Stopped)')
        shared.entities[ID].runningCircle.Stop()
        runningActions[ID][1].set()
        if len(runningActions[ID]) == 4:
            runningActions[ID][3].set()

def RunProcess(action, queue, pause, stop, error, sharedMemoryName, shape, dtype, **kwargs):
    '''Accepts an entity `ID`, and other `args` to pass to the Run() method of the entity's action.'''
    pause.clear()
    stop.clear()
    error.clear()
    queue.put(action.Run(pause, stop, error, sharedMemoryName, shape, dtype, **kwargs))

def WaitForSaveToFinish(entity, saveProcess, deltaTime, lastTime):
    deltaTime += time.time() - lastTime
    lastTime = time.time()
    if not runningActions[entity.ID][3]:
        if deltaTime < .1:
            return threading.Timer(.1, WaitForSaveToFinish, args = (entity, saveProcess, deltaTime, lastTime))
        print('Setting save STOP')
        runningActions[entity.ID][3].set()
        deltaTime = 0

    if runningActions[entity.ID][3].is_set():
        if deltaTime > maxWait:
            shared.workspace.assitant.PushMessage(f'It took too long to save {entity.name}\'s data. This was triggered to allow the app to safely exit the process without hanging. Either check for errors, or extend the *maxWait* in utils/multiprocessing.py')
        else:
            threading.Timer(.1, WaitForSaveToFinish, args = (entity, saveProcess, deltaTime, lastTime))
            return
    else:
        saveProcess.join()

def CheckProcess(entity, process: Process, saveProcess: Process, queue: Queue, getRawData = True, saving = False):
    if queue.empty():
        threading.Timer(.1, CheckProcess, args = (entity, process, saveProcess, queue, getRawData, saving)).start()
        return
    process.join()
    # Has an error occured to cause the stop?
    if runningActions[entity.ID][2].is_set():
        print('A critical error occurred!')
        shared.workspace.assistant.PushMessage(queue.get(), 'Critical Error')
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Corrupted)')
        entity.runningCircle.Stop()
    else:
        # Has the action completed successfully?
        if not runningActions[entity.ID][1].is_set():
            entity.title.setText(f'{entity.title.text().split(' (')[0]} (Holding Data)')
            entity.runningCircle.Stop()
            shared.workspace.assistant.PushMessage(f'{entity.name} has finished and is no longer running.')
        else:
            StopAction(entity)
            shared.workspace.assistant.PushMessage('Stopped action(s).')

    if saving:
        # runningActions[entity.ID][3].set()
        WaitForSaveToFinish(entity, saveProcess, 0, time.time())

    runningActions.pop(entity.ID)

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
    entity.data[:] = np.nan # Initialise data array to NaNs.
        
    queue = Queue()
    action = entity.offlineAction if not entity.online else entity.onlineAction
    # Define the pause and stop events and add them to the runningActions dict.
    runningActions[entity.ID] = [Event(), Event(), Event()] # pause, stop, error
    # Instantiate a process
    process = Process(
        target = RunProcess,
        args = (action, queue, runningActions[entity.ID][0], runningActions[entity.ID][1], runningActions[entity.ID][2], entity.dataSharedMemory.name, emptyDataArray.shape, emptyDataArray.dtype),
        kwargs = kwargs
    )
    # Check if this block is attached to a save block
    saving = False
    saveProcess = None
    for ID in entity.linksOut:
        if ID == 'free':
            continue
        if shared.entities[ID].type == 'Save':
            saving = True
            runningActions[entity.ID].append(Event())
            runningActions[entity.ID][3].clear()
            # Instantiate a save process
            shared.entities[ID].stream = entity.streams['raw']()
            saveProcess = Process(
                target = shared.entities[ID].StartSaveCheck,
                args = (runningActions[entity.ID][3], entity.dataSharedMemory.name, emptyDataArray.shape, emptyDataArray.dtype)
            )
            saveProcess.start()
            break
    entity.runningCircle.Start()
    entity.title.setText(f'{entity.name.split(' (')[0]} (Running)')
    process.start()
    # periodically check if the action has finished ...
    threading.Timer(.1, CheckProcess, args = (entity, process, saveProcess, queue, kwargs['getRawData'], saving)).start()
    return True