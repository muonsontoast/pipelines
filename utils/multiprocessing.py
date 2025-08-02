from multiprocessing import Queue, Process, Event
import threading
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

def RunProcess(action, queue, pause, stop, *args, **kwargs):
    '''Accepts an entity `ID`, and other `args` to pass to the Run() method of the entity's action.'''
    # (self, pause, numSteps, stepKick, repeats, numParticles = 10000, getRawData = True):
    pause.clear()
    stop.clear()
    queue.put(action.Run(pause, stop, *args, **kwargs))

def CheckProcess(entity, process: Process, queue: Queue, getRawData = True, postProcessedData = ''):
    if queue.empty():
        threading.Timer(.1, CheckProcess, args = (entity, process, queue, getRawData, postProcessedData)).start()
        return
    process.join()
    runningActions.pop(entity.ID)
    if getRawData:
        print('Saving raw data only')
        entity.data = queue.get()
    else:
        print('Saving raw data AND post processed data')
        data, postData = queue.get()
        entity.data = data
        setattr(entity, postProcessedData, postData)
    entity.runningCircle.Stop()
    if entity.data is not None:
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Holding Data)')
        shared.workspace.assistant.PushMessage('Finished orbit response measurement.')
    else:
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Empty)')
        shared.workspace.assistant.PushMessage('Stopped action(s).')

def PerformAction(entity, *args, **kwargs) -> bool:
    '''Set `getRawData` to False to perform post processing, supplying an attribute name `postProcessedData` for the post processed data to be stored at.\n
    Returns True if successful else False.'''
    if entity.ID in runningActions:
        if runningActions[entity.ID][0].is_set():
            TogglePause(entity, False)
            return True
        else:
            return False
    entity.runningCircle.Start()
    entity.title.setText(f'{entity.name.split(' (')[0]} (Running)')
    kwargs['getRawData'] = kwargs.pop('getRawData', True)
    postProcessedData = kwargs.pop('postProcessedData', '')
    queue = Queue()
    action = entity.offlineAction if not entity.online else entity.offline
    # Define the pause and stop events and add them to the runningActions dict.
    runningActions[entity.ID] = [Event(), Event()]
    process = Process(
        target = RunProcess, 
        args = (action, queue, runningActions[entity.ID][0], runningActions[entity.ID][1], *args),
        kwargs = kwargs
    )
    process.start()
    # periodically check if the action has finished ...
    threading.Timer(.1, CheckProcess, args = (entity, process, queue, kwargs['getRawData'], postProcessedData)).start()
    return True