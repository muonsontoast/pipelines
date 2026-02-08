from PySide6.QtCore import QThread, Signal
from threading import Event
import psutil
from pynvml import *

class ResourceMonitor(QThread):
    GPUSignal = Signal(str)
    RAMSignal = Signal(str)
    diskSignal = Signal(str)

    def __init__(self):
        super().__init__()
        self.running = False
        self.stopEvent = Event()
        try:
            nvmlInit()
            self.GPUHandle = nvmlDeviceGetHandleByIndex(0)
            self.hasGPU = True
            self.GPUName = ''
            self.GPUMemoryUsed = 0
            self.GPUMemoryTotal = 0
        except:
            self.hasGPU = False

    def PollGPU(self):
        if not self.hasGPU:
            return self.GPUSignal.emit(
                'GPU:\t\tNo dedicated NVIDIA GPU detected.'
            )

        if self.GPUName == '':
            self.GPUName = nvmlDeviceGetName(self.GPUHandle).split('GPU')[0]
        memoryHandle = nvmlDeviceGetMemoryInfo(self.GPUHandle)
        self.GPUMemoryUsed = memoryHandle.used / 1024 ** 3
        self.GPUMemoryTotal = memoryHandle.total / 1024 ** 3
        self.GPUSignal.emit(
            f'GPU:\t\t{self.GPUName} ({self.GPUMemoryUsed:.1f} / {self.GPUMemoryTotal:.1f} GB)'
        )
    
    def PollRAM(self):
        try:
            self.RAM = psutil.virtual_memory() # given in Byte
            self.RAMGB = self.RAM.total / 1024 ** 3 # convert to GB
            self.RAMSignal.emit(
                f'RAM:\t\t{self.RAM.percent * self.RAMGB * 1e-2:.1f} / {self.RAMGB:.1f} GB'
            )
        except:
            self.RAMSignal.emit(
                f'RAM:\t\tUnable to fetch RAM info.'
            )

    def PollDisk(self):
        try:
            self.disk = psutil.disk_usage('/')
            self.diskUsed = self.disk.used / 1024 ** 3
            self.diskTotal = self.disk.total / 1024 ** 3
            self.diskSignal.emit(
                f'Disk:\t\t{self.diskUsed:.1f} / {self.diskTotal:.1f} GB'
            )
        except:
            self.diskSignal.emit(
                f'Disk:\t\tUnable to fetch disk info.'
            )

    def FetchResourceValues(self):
        while True:
            self.PollGPU()
            self.PollRAM()
            self.PollDisk()
            if self.stopEvent.wait(timeout = 1):
                break