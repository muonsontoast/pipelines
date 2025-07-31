from multiprocessing import Queue, Process
import threading
from .. import shared

def RunProcess(action, isOnline, queue, *args, **kwargs):
    '''Accepts an entity `ID`, and other `args` to pass to the Run() method of the entity's action.'''
    queue.put(action.Run(isOnline, *args, **kwargs))

def CheckProcess(entity, process: Process, queue: Queue, getRawData = True, postProcessedData = ''):
    if queue.empty():
        threading.Timer(.1, CheckProcess, args = (entity, process, queue, getRawData, postProcessedData)).start()
        return
    print('Action FINISHED, cleaning up ...')
    process.join()
    if getRawData:
        print('Saving raw data only')
        entity.data = queue.get()
    else:
        print('Saving raw data and post processed data')
        data, postData = queue.get()
        entity.data = data
        setattr(entity, postProcessedData, postData)
        print('raw data shape', entity.data.shape)
        print('ORM shape', entity.ORM.shape)
    entity.runningCircle.stop = True
    if hasattr(entity, 'title'):
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Holding Data)')
    shared.workspace.assistant.PushMessage('Finished orbit response measurement.')

def PerformAction(entity, isOnline, *args, **kwargs):
    '''Set `getRawData` to False to perform post processing, supplying an attribute name `postProcessedData` for the post processed data to be stored at.'''
    kwargs['getRawData'] = kwargs.get('getRawData', True)
    postProcessedData = kwargs.pop('postProcessedData', '')
    # kwargs['postProcessedData'] = kwargs.get('postProcessedData', '')
    queue = Queue()
    process = Process(
        target = RunProcess, 
        args = (entity.action, isOnline, queue, *args),
        kwargs = kwargs
    )
    process.start()
    # periodically check if the action has finished ...
    threading.Timer(.1, CheckProcess, args = (entity, process, queue, kwargs['getRawData'], postProcessedData)).start()