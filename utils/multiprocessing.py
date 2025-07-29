from multiprocessing import Queue, Process
import threading

def RunProcess(action, isOnline, queue, *args):
    '''Accepts an entity `ID`, and other `args` to pass to the Run() method of the entity's action.'''
    queue.put(action.Run(isOnline, *args))

def CheckProcess(entity, process: Process, queue: Queue):
    if queue.empty():
        threading.Timer(.1, CheckProcess, args = (entity, process, queue)).start()
        return
    print('Action FINISHED, cleaning up ...')
    process.join()
    entity.data = queue.get()
    entity.runningCircle.Stop()
    if hasattr(entity, 'title'):
        entity.title.setText(f'{entity.title.text().split(' (')[0]} (Holding Data)')

def PerformAction(entity, isOnline, *args):
    queue = Queue()
    process = Process(target = RunProcess, args = (entity.action, isOnline, queue, *args))
    process.start()
    # periodically check if the action has finished ...
    threading.Timer(.1, CheckProcess, args = (entity, process, queue)).start()