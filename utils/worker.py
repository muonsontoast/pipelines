from PySide6.QtCore import QObject, QThread, Signal, Slot
import time
import numpy as np

class Worker(QObject):
    '''Worker to handle long-running tasks '''
    finished = Signal()
    progress = Signal(int)
    start = Signal()

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args
        self.data = None
        self.start.connect(self.Run)

    @Slot()
    def Run(self):
        '''Accepts a `block`, function `func` to run, with optional `steps` for returning progress.'''
        t = time.time()
        self.data = self.func(*self.args)
        print(f'Job finished after {time.time() - t:.3f} seconds.')
        self.finished.emit()