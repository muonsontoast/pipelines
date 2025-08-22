import pandas as pd
import os
import time
import numpy as np
from multiprocessing.shared_memory import SharedMemory
from datetime import datetime
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QListView, QFileSystemModel, QGraphicsProxyWidget, 
    QHBoxLayout, QVBoxLayout, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QTimer, QModelIndex, QSortFilterProxyModel, QItemSelectionModel
from .draggable import Draggable
from .. import shared
from .. import style

class Save(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'Save'), type = 'Save', size = kwargs.pop('size', [600, 300]), **kwargs)
        self.parent = parent
        self.rate = kwargs.get('rate', 4) # save rate in Hz
        self.timeBetweenSaves = 1 / self.rate # in seconds
        self.timestamp = None
        self.stream = None
        self.firstPass = True
        self.FSModel = QFileSystemModel()
        self.FSModel.setRootPath('')
        self.proxyModel = QSortFilterProxyModel(self)
        self.proxyModel.setSourceModel(self.FSModel)
        self.proxyModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxyModel.setFilterKeyColumn(0) # Filter by names
        self.path = os.path.join(shared.cwd, 'datadump')
        self.currentIndex = QModelIndex()
        self.UndoPathList = [] # a list of previous paths for undo
        self.RedoPathList = [] # a list of future paths for redo
        self.setMouseTracking(True)
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
            'entityNameIn': shared.entities[next(iter(self.linksIn))].name,
            'path': self.path,
        }
    
    def __setstate__(self, state):
        self.timeBetweenSaves = state['timeBetweenSaves']
        self.timestamp = state['timestamp']
        self.stream = state['stream']
        self.entityNameIn = state['entityNameIn']
        self.path = state['path']
        self.firstPass = True

    def Push(self):
        self.main = QWidget()
        self.main.setLayout(QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget()
        self.widget.setFocusPolicy(Qt.StrongFocus)
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
        # Save path
        self.saveWidget = QWidget()
        self.saveWidget.setLayout(QVBoxLayout())
        self.saveWidget.layout().setContentsMargins(10, 10, 10, 10)
        self.savePath = QLineEdit(self.path)
        self.savePath.setCursorPosition(0)
        self.savePath.setFixedHeight(35)
        self.savePath.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.savePath.textChanged.connect(self.ChangePathText)
        self.savePath.returnPressed.connect(self.ConfirmPathText)
        self.saveTitle = QLabel('Output Path')
        self.saveWidget.layout().addWidget(self.saveTitle)
        self.saveWidget.layout().addWidget(self.savePath)
        # Paths list view widget
        pathsWidget = QWidget()
        pathsWidget.setLayout(QVBoxLayout())
        pathsWidget.layout().setContentsMargins(10, 10, 10, 10)
        self.paths = QListView()
        self.paths.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.paths.setFocusPolicy(Qt.NoFocus)
        self.paths.setFrameShape(QListView.NoFrame)
        self.paths.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.paths.setModel(self.proxyModel)
        self.paths.setModelColumn(0)
        self.paths.setUniformItemSizes(True)
        self.paths.setUpdatesEnabled(True)
        self.dirName = os.path.dirname(self.path)
        self.FSModel.setRootPath(self.dirName)
        initialIndex = self.FSModel.index(os.path.basename(self.dirName))
        self.paths.setRootIndex(self.proxyModel.mapFromSource(initialIndex))
        pathsWidget.layout().addWidget(self.paths)
        self.widget.layout().addWidget(self.saveWidget)
        self.widget.layout().addWidget(pathsWidget)
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.main.layout().addWidget(self.widget)
        self.AddSocket('data', 'F', acceptableTypes = ['PV', 'Corrector', 'BPM', 'Single Task GP', 'Orbit Response', 'View'])
        super().Push()

    def GetIndexFromString(self, pattern):
        matches = self.paths.model().match(
            self.paths.model().index(0, 0, self.paths.rootIndex()),
            Qt.DisplayRole,
            pattern,
            hits = 1,
            flags = Qt.MatchStartsWith,
        )
        if matches:
            self.paths.setCurrentIndex(matches[0])
            self.paths.selectionModel().select(matches[0], QItemSelectionModel.ClearAndSelect)

    def IncrementShortcutIndex(self):
        if self.currentIndex == QModelIndex():
            self.currentIndex = 0
        else:
            self.currentIndex = max(min(self.currentIndex + 1, self.paths.model().rowCount(self.paths.rootIndex()) - 1), 0)
        index = self.paths.model().index(self.currentIndex, 0, self.paths.rootIndex())
        self.paths.setCurrentIndex(index)
        self.paths.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)

    def DecrementShortcutIndex(self):
        if self.currentIndex == QModelIndex():
            self.currentIndex = self.paths.model().rowCount(self.paths.rootIndex()) - 1
        else:
            self.currentIndex = max(min(self.currentIndex - 1, self.paths.model().rowCount(self.paths.rootIndex()) - 1), 0)
        index = self.paths.model().index(self.currentIndex, 0, self.paths.rootIndex())
        self.paths.setCurrentIndex(index)
        self.paths.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        if angle < 0:
            self.IncrementShortcutIndex()
        else:
            self.DecrementShortcutIndex()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self.DecrementShortcutIndex()
        elif event.key() == Qt.Key_Down:
            self.IncrementShortcutIndex()
        elif event.key() == Qt.Key_Return:
            choice = self.paths.model().index(self.currentIndex, 0, self.paths.rootIndex()).data()
            self.savePath.setText(os.path.join(os.path.dirname(self.savePath.text()), f'{choice}\\'))
            
        event.accept()

    def ChangePathText(self):
        dirName = os.path.dirname(self.savePath.text())
        if os.path.isdir(dirName) and dirName != self.dirName:
            self.dirName = dirName
            self.FSModel.setRootPath(self.dirName)
            index = self.FSModel.index(self.dirName)
            self.paths.setRootIndex(self.proxyModel.mapFromSource(index))
            self.path = self.savePath.text()
        else:
            self.GetIndexFromString(os.path.basename(self.savePath.text()))

    def ConfirmPathText(self):
        savePath = QLineEdit(self.savePath.text())
        savePath.setCursorPosition(0)
        savePath.setFixedHeight(35)
        savePath.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        savePath.textChanged.connect(self.ChangePathText)
        savePath.returnPressed.connect(self.ConfirmPathText)
        self.saveWidget.layout().replaceWidget(self.savePath, savePath)
        self.savePath.setParent(None)
        self.savePath.deleteLater()
        def ReassignLineEdit():
            self.path = savePath.text()
            self.savePath = savePath
            self.BaseStyling()
            shared.workspace.assistant.PushMessage(f'Path updated for {self.name}')
        QTimer.singleShot(0, ReassignLineEdit)

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
            if len(entity.data.shape) == 0:
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
        df.to_parquet(os.path.join(self.path, f'{self.entityNameIn} ({timestamp.strftime('%Y-%m-%d')} at {timestamp.strftime('%H-%M-%S')}).parquet'), engine = 'pyarrow', index = True)

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
        self.savePath.setStyleSheet(style.LineEditStyle(color = '#3e3e3e', fontColor = '#c4c4c4', paddingLeft = 5))
        self.paths.setStyleSheet(style.ListView(color = '#2e2e2e', hoverColor = '#363636', fontColor = '#c4c4c4', spacing = 5))
        self.paths.horizontalScrollBar().setStyleSheet(style.ScrollBarStyle(handleColor = '#3d3d3d', backgroundColor = '#2e2e2e'))
        self.paths.verticalScrollBar().setStyleSheet(style.ScrollBarStyle(handleColor = '#3d3d3d', backgroundColor = '#2e2e2e'))
