import pandas as pd
import os
import time
import numpy as np
from multiprocessing.shared_memory import SharedMemory
from datetime import datetime
from datetime import datetime
from PySide6.QtWidgets import QWidget, QLabel, QGraphicsProxyWidget, QHBoxLayout, QVBoxLayout, QSizePolicy, QSpacerItem
from PySide6.QtCore import Qt
from .draggable import Draggable
from ..utils.multiprocessing import runningActions
from .. import shared
from .. import style

class Save(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'Save'), type = 'Save', size = kwargs.pop('size', [500, 200]), **kwargs)
        self.parent = parent
        self.rate = kwargs.get('rate', 4) # save rate in Hz
        self.timeBetweenSaves = 1 / self.rate # in seconds
        self.timestamp = None
        self.stream = None
        self.firstPass = True
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.Push()
        self.BaseStyling()

    def __getstate__(self):
        return {
            'timeBetweenSaves': self.timeBetweenSaves,
            'timestamp': self.timestamp,
            'stream': self.stream,
            'entityNameIn': shared.entities[next(iter(self.linksIn))].name
        }
    
    def __setstate__(self, state):
        self.timeBetweenSaves = state['timeBetweenSaves']
        self.timestamp = state['timestamp']
        self.stream = state['stream']
        self.entityNameIn = state['entityNameIn']
        self.firstPass = True

    def Push(self):
        self.main = QWidget()
        self.main.setLayout(QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget()
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QVBoxLayout())
        self.widget.layout().setContentsMargins(0, 0, 0, 0)
        self.widget.layout().setSpacing(0)
        # Header
        header = QWidget()
        header.setLayout(QHBoxLayout())
        header.setStyleSheet(style.WidgetStyle(color = "#828282", borderRadiusTopLeft = 8, borderRadiusTopRight = 8))
        header.setFixedHeight(40)
        header.layout().setContentsMargins(15, 0, 15, 0)
        self.title = QLabel(f'{self.settings['name']} (Disconnected)')
        header.layout().addWidget(self.title, alignment = Qt.AlignLeft)
        self.widget.layout().addWidget(header)
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.main.layout().addWidget(self.widget)
        self.AddSocket('data', 'F', acceptableTypes = ['PV', 'Corrector', 'BPM', 'Single Task GP', 'Orbit Response', 'View'])
        super().Push()

    def StartSaveCheck(self, shouldStop, sharedMemoryName, shape, dtype):
        '''This method gets called by the multiprocessing script when launching an action, if it's attached to an action being launched.'''
        timestamp = datetime.now()
        dataSharedMemory = SharedMemory(name = sharedMemoryName)
        self.dataIn = np.ndarray(shape, dtype, buffer = dataSharedMemory.buf)
        while not shouldStop.is_set():
            self.Save(timestamp)
            time.sleep(self.timeBetweenSaves)
        self.firstPass = True
        dataSharedMemory.close()
        dataSharedMemory.unlink()

    def Save(self, timestamp = None):
        # The following checks are only necessary when attaching another block to this save block
        if timestamp is None:
            # Is this connected to another block?
            if not self.linksIn:
                return
            # Retrieve the data held by the connected block
            entity = shared.entities[next(iter(self.linksIn))]
            self.entityNameIn = entity.name
            # Is the connected block already holding data?
            if len(self.entity.data.shape) == 0:
                return
        # First time setup
        if self.firstPass:
            if timestamp is None:
                self.stream = entity.streams['raw']()
                self.dataIn = self.stream['data']
            self.index = pd.MultiIndex.from_product(
                [self.stream['names'][_] for _ in range(len(self.dataIn.shape[:-1]))],
                names = self.stream['ax'], # specifially axis names
            )
            self.cols = self.stream['names'][-1]
            self.firstPass = False
        dataIn = self.dataIn.reshape(-1, self.dataIn.shape[-1])
        df = pd.DataFrame(dataIn, index = self.index, columns = self.cols)
        timestamp = datetime.now() if timestamp is None else timestamp
        df.to_parquet(os.path.join(shared.cwd, 'datadump', f'{self.entityNameIn} ({timestamp.strftime('%Y-%m-%d')} at {timestamp.strftime('%H-%M-%S')}).parquet'), engine = 'pyarrow', index = True)

    def AddLinkIn(self, ID, socket):
        # Allow only one block to connect to a view block at any one time.
        if self.linksIn:
            super().RemoveLinkIn(next(iter(self.linksIn)))
        super().AddLinkIn(ID, socket)
        self.title.setText(f'{self.settings['name']} (Connected)')
        entity = shared.entities[next(iter(self.linksIn))]
        if len(entity.data) > 0:
            self.firstPass = True
            self.Save()
        else:
            shared.workspace.assistant.PushMessage(f'{entity.name} has been attached to {self.name} but it isn\'t holding any data', 'Warning')

    def RemoveLinkIn(self, ID):
        super().RemoveLinkIn(ID)
        self.title.setText(f'{self.settings['name']} (Disconnected)')

    def BaseStyling(self):
        self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 12))
        self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 18, fontColor = '#c4c4c4'))
