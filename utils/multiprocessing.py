import gc # garbage collection
from multiprocessing import Queue, Process, Event, Value
from ctypes import c_float
import multiprocessing as mp
mp.set_start_method('spawn', force = True) # force linux machines to call __getstate__ and __setstate__ methods attached to actions.
import threading
import numpy as np
import time
from datetime import timedelta
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
    else:
        entity.title.setText(entity.name)
    return state

def StopAction(entity, restart = False):
    '''Stop an entity's action if it is running. Returns true if successful else false.'''
    if entity.ID in runningActions:
        runningActions[entity.ID][1].set()
        with entity.lock:
            if hasattr(entity, 'actionFinished'):
                if hasattr(entity, 'restartApplied'):
                    if restart:
                        entity.restartApplied.set()
                entity.actionFinished.set()
        entity.title.setText(entity.name)
        return True
    else:
        return False

def StopActions():
    '''Stop all currently running actions.'''
    IDs = list(runningActions.keys())
    for ID in IDs:
        shared.entities[ID].title.setText(shared.entities[ID].name)
        runningActions[ID][1].set()

def RunProcess(action, queue, pause, stop, error, progress, sharedMemoryName, shape, dtype, **kwargs):
    '''Accepts an entity `ID`, and other `args` to pass to the Run() method of the entity's action.'''
    pause.clear()
    stop.clear()
    error.clear()
    queue.put(action.Run(pause, stop, error, progress, sharedMemoryName, shape, dtype, **kwargs))

def WaitForSaveToFinish(entity, saveProcess, deltaTime, lastTime):
    deltaTime += time.time() - lastTime
    lastTime = time.time()
    if not runningActions[entity.ID][3]:
        if deltaTime < .1:
            return threading.Timer(.1, WaitForSaveToFinish, args = (entity, saveProcess, deltaTime, lastTime))
        runningActions[entity.ID][3].set()
        deltaTime = 0

    if runningActions[entity.ID][3].is_set():
        if deltaTime > maxWait:
            shared.workspace.assitant.PushMessage(f'It took too long to save {entity.name}\'s data. This was triggered to allow the app to safely exit the process without hanging. Either check for errors, or extend the *maxWait* in utils/multiprocessing.py')
        else:
            threading.Timer(.1, WaitForSaveToFinish, args = (entity, saveProcess, deltaTime, lastTime))
    else:
        saveProcess.join()

def CheckProcess(entity, process: Process, saveProcess: Process, queue: Queue, getRawData = True, saving = False, autoCompleteProgress = True, ignorePrint = False, timeRunning = 0):
    while process.is_alive():
        if entity.ID in shared.runnableBlocks:
            if hasattr(entity, 'progressBar'):
                if not runningActions[entity.ID][2].is_set():
                    entity.progressBar.CheckProgress(runningActions[entity.ID][3].value)
            entity.runTimeEdit.setText(str(timedelta(seconds = int(time.time() - entity.t0 + timeRunning))))
            entity.progressEdit.setText(f'{entity.progressBar.progress * 1e2:.0f}')
        if runningActions[entity.ID][1].wait(timeout = .1):
            break
    runningActions[entity.ID][1].clear()
    # Has an error occured to cause the stop?
    if runningActions[entity.ID][2].is_set():
        print(f'A critical error occurred inside {entity.name}')
        shared.workspace.assistant.PushMessage(queue.get(), 'Critical Error')
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Corrupted)')
    else:
        # Has the action completed successfully?
        if not runningActions[entity.ID][1].is_set():
            if not ignorePrint:
                shared.workspace.assistant.PushMessage(f'{entity.name} has finished and is no longer running.')
            entity.progressBar.CheckProgress(1) if autoCompleteProgress else None
        else:
            StopAction(entity)
            shared.workspace.assistant.PushMessage(f'Stopped and reset {entity.name}.')

    if saving:
        WaitForSaveToFinish(entity, saveProcess, 0, time.time())

    # close the shared memory of the entity to free up system resources.
    process.terminate()
    process.join()
    runningActions.pop(entity.ID)
    entity.dataSharedMemory.close()
    entity.dataSharedMemory.unlink()
    del entity.dataSharedMemory
    gc.collect()
    if hasattr(entity, 'actionFinished'):
        with entity.lock:
            if hasattr(entity, 'restartApplied'):
                entity.restartApplied.clear()
            entity.actionFinished.set()

def PerformAction(entity: Entity, emptyDataArray: np.ndarray, **kwargs) -> bool:
    '''Set `getRawData` to False to perform post processing.\n
    Supply an `emptyDataArray` numpy array of the final shape.\n
    Supply an attribute name `postProcessedDataName` for the post processed data to be stored in.\n
    If post processing, also supply an `emptyPostProcessedDataArray` numpy array of the final shape.\n
    Returns True if successful else False.'''
    if hasattr(entity, 'resetApplied'):
        entity.resetApplied.clear()
    if entity.ID in runningActions:
        if runningActions[entity.ID][0].is_set():
            TogglePause(entity, False)
            return True
        else:
            return False
    if hasattr(entity, 'progressBar') and kwargs.pop('updateProgress', True):
        entity.progressBar.Reset()
    progress = kwargs.pop('progress', 0.)
    ignorePrint = kwargs.pop('ignorePrint', False)
    timeRunning = kwargs.pop('timeRunning', 0)
    autoCompleteProgress = kwargs.pop('autoCompleteProgress', True)
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
            return
    entity.CreateEmptySharedData(emptyDataArray) # share the data with the process.
    entity.data[:] = np.inf # Initialise data array to infs.
    print(f'Reserved {entity.data.nbytes / (1024 ** 2):.0f} MB of system memory for {entity.name}')
    
    queue = Queue()
    action = entity.offlineAction if not entity.online else entity.onlineAction
    # Define the pause and stop events and progress and add them to the runningActions dict.
    runningActions[entity.ID] = [Event(), Event(), Event(), Value(c_float, progress)] # pause, stop, error, progress
    # Instantiate a process
    process = Process(
        target = RunProcess,
        args = (action, queue, runningActions[entity.ID][0], runningActions[entity.ID][1], runningActions[entity.ID][2], runningActions[entity.ID][3], entity.dataSharedMemory.name, emptyDataArray.shape, emptyDataArray.dtype),
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
    process.start()
    # periodically check if the action has finished ...
    threading.Thread(target = CheckProcess, args = (entity, process, saveProcess, queue, kwargs['getRawData'], saving, autoCompleteProgress, ignorePrint, timeRunning), daemon = True).start()
    return True