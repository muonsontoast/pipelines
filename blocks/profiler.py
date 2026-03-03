from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QSizePolicy, QGridLayout, QHBoxLayout, QVBoxLayout, QSpacerItem
from PySide6.QtCore import Qt, Signal
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
from matplotlib import ticker
from threading import Thread
from cycler import cycler
mplstyle.use('fast')
from collections import deque
import time
import pandas as pd
import numpy as np
from pathlib import Path
from .draggable import Draggable
from .pv import PV
from .. import shared
from .. import style

plt.rcParams['text.usetex'] = False
plt.rcParams['font.size'] = 2

class Profiler(Draggable):
    updatePlotSignal = Signal()
    def __init__(self, parent, proxy, **kwargs):
        super().__init__(
            proxy,
            name = kwargs.pop('name', 'Profiler'),
            type = 'Profiler',
            size = kwargs.pop('size', [650, 525]),
            windowSizeInSeconds = kwargs.pop('windowSizeInSeconds', 30), # captures the last 60 seconds of profiling data by default.
            postProcessOption = kwargs.pop('postProcessOption', 'raw'), # options are 'raw', 'mean', 'stddev'.
            headerColor = "#2E30C7",
            **kwargs
        )
        self.updatePlotSignal.connect(self.UpdatePlot)
        self.pollPeriod = .1
        # A dataframe to store profiling data.
        self.data = pd.DataFrame(columns = ['timestamp'])
        self.lineData = {}
        self.Push()
        self.BaseStyling()
        self.SelectTimeWindow()
        self.SelectPostProcessOption()
        self.postProcessOptionWasChanged = False
        self.saveName = None
        Thread(target = self.FetchValues).start()

    def Start(self):
        if self.data.shape[0] == 0:
            return np.nan
        self.stopCheckThread.wait(timeout = self.settings['windowSizeInSeconds'])
        return self.lineData[next(iter(self.lineData))][0]

    def UpdatePlot(self):
        self.canvas.restore_region(self.background)
        nowTime = time.time()
        mn, mx = self.ax.get_ylim()
        newMn, newMx = self.ax.get_ylim()
        for ID in self.linksIn:
            try:
                y = self.data[ID]
                if self.postProcessOptionWasChanged:
                    self.data = self.data.iloc[-1:]
                    self.data.index = [0]
                    y = self.data[ID]
                    self.lineData[ID] = deque([])

                if self.settings['postProcessOption'] != 'raw':
                    if self.settings['postProcessOption'] == 'mean':
                        self.lineData[ID].append(np.nanmean(y))
                    elif self.settings['postProcessOption'] == 'stddev':
                        self.lineData[ID].append(np.nanstd(y))
                    while len(self.lineData[ID]) > self.data.shape[0]:
                        self.lineData[ID].popleft()
                else:
                    self.lineData[ID] = deque(y)
            except:
                continue
            x = nowTime - self.data['timestamp'] - self.pollPeriod
            if self.settings['windowSizeInSeconds'] > 60:
                x /= 60
            newMn = min(newMn, np.nanmin(self.lineData[ID]))
            newMx = max(newMx, np.nanmax(self.lineData[ID]))
            self.plotLines[ID].set_data(x, self.lineData[ID])
            if len(self.data) > 0:
                try:
                    self.ax.draw_artist(self.plotLines[ID])
                except:
                    pass
        if not newMn == mn or not newMx == mx:
            rng = newMx - newMn if newMn != newMx else 1
            if not np.isinf(newMn) and not np.isinf(newMx):
                self.ax.set_ylim(newMn - .25 * rng, newMx + .25 * rng)
                self.canvas.draw()
        self.canvas.blit(self.ax.bbox)
        if self.postProcessOptionWasChanged:
            self.postProcessOptionWasChanged = False
            self.saveName = f'profiler_{'_'.join([''.join(''.join('-'.join((' '.join(shared.entities[ID].name.split(':'))).split()).split('(')).split(')')) for ID in self.linksIn])}_{self.settings['postProcessOption']}_{self.timestamp}.csv'
            self.savePath = Path(shared.cwd) / 'datadump' / self.saveName
            self.data.to_csv(self.savePath, index = False)
        elif self.data.shape[0] > 0:
            self.data.iloc[-1:].to_csv(self.savePath, mode = 'a', index = False, header = False)

    def Push(self):
        super().Push()
        self.AddSocket('in', 'F', acceptableTypes = [PV])
        self.AddSocket('out', 'M')
        self.widget = QWidget()
        self.main.layout().addWidget(self.widget)
        self.widget.setLayout(QGridLayout())
        self.widget.layout().setContentsMargins(10, 10, 10, 10)
        self.widget.layout().setSpacing(15)
        self.figure = Figure(figsize = (11, 5), dpi = 300)
        self.figure.set_animated(True)  # Enable blitting for faster redraws
        self.figure.subplots_adjust(left = .135, right = .95, top = .975, bottom = .25)
        self.figure.set_facecolor('none')
        self.plotLines = {}
        self.ax = self.figure.add_subplot(111)
        self.ax.minorticks_on()
        self.ax.set_facecolor('none')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#6e6e6e')
            spine.set_linewidth(.5)
        self.ax.tick_params(axis = 'both', which = 'major', colors = '#6e6e6e', labelsize = 4, width = .5, length = 3)
        self.ax.tick_params(axis = 'both', which = 'minor', colors = '#6e6e6e', labelsize = 4, width = .25, length = 1.5)
        for label in self.ax.get_xticklabels() + self.ax.get_yticklabels():
            label.set_color('#6e6e6e')
        self.ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins = 10))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedHeight(300)
        self.canvas.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.canvas.setStyleSheet('background-color: transparent')
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.widget.layout().addWidget(self.canvas, 1, 0, 1, 4)
        # Adjust window size
        self.windowWidget = QWidget()
        self.windowWidget.setLayout(QVBoxLayout())
        self.windowWidget.layout().setContentsMargins(5, 0, 0, 0)
        self.windowWidget.layout().setSpacing(5)
        self.windowSize = QWidget()
        self.windowSize.setLayout(QHBoxLayout())
        self.windowSize.layout().setContentsMargins(15, 0, 20, 0)
        self.windowSize.layout().setSpacing(5)
        self.trailingBtns = []
        self.trailing5secBtn = QPushButton('5 sec')
        self.trailing5secBtn.clicked.connect(lambda: self.SelectTimeWindow(5))
        self.trailingBtns.append(self.trailing5secBtn)
        self.trailing10secBtn = QPushButton('10 sec')
        self.trailing10secBtn.clicked.connect(lambda: self.SelectTimeWindow(10))
        self.trailingBtns.append(self.trailing10secBtn)
        self.trailing30secBtn = QPushButton('30 sec')
        self.trailing30secBtn.clicked.connect(lambda: self.SelectTimeWindow(30))
        self.trailingBtns.append(self.trailing30secBtn)
        self.trailing1minBtn = QPushButton('1 min')
        self.trailing1minBtn.clicked.connect(lambda: self.SelectTimeWindow(60))
        self.trailingBtns.append(self.trailing1minBtn)
        self.trailing5minBtn = QPushButton('5 min')
        self.trailing5minBtn.clicked.connect(lambda: self.SelectTimeWindow(300))
        self.trailingBtns.append(self.trailing5minBtn)
        self.trailing15minBtn = QPushButton('15 min')
        self.trailing15minBtn.clicked.connect(lambda: self.SelectTimeWindow(900))
        self.trailingBtns.append(self.trailing15minBtn)
        for btn in self.trailingBtns:
            btn.setFixedWidth(80)
        self.windowSize.layout().addWidget(self.trailing5secBtn)
        self.windowSize.layout().addWidget(self.trailing10secBtn)
        self.windowSize.layout().addWidget(self.trailing30secBtn)
        self.windowSize.layout().addWidget(self.trailing1minBtn)
        self.windowSize.layout().addWidget(self.trailing5minBtn)
        self.windowSize.layout().addWidget(self.trailing15minBtn)
        self.windowWidget.layout().addWidget(QLabel('TIME WINDOW'), alignment = Qt.AlignLeft | Qt.AlignVCenter)
        self.windowWidget.layout().addWidget(self.windowSize)
        self.widget.layout().addWidget(self.windowWidget, 2, 0, 2, 4)
        # Post Processing Options
        self.postprocessWidget = QWidget()
        self.postprocessWidget.setLayout(QVBoxLayout())
        self.postprocessWidget.layout().setContentsMargins(5, 0, 0, 0)
        self.postprocessWidget.layout().setSpacing(5)
        self.postprocessBtns = []
        self.postprocessData = QWidget()
        self.postprocessData.setLayout(QHBoxLayout())
        self.postprocessData.layout().setContentsMargins(15, 0, 20, 0)
        self.postprocessData.layout().setSpacing(3)
        self.rawBtn = QPushButton('Raw')
        self.rawBtn.clicked.connect(lambda: self.SelectPostProcessOption('raw'))
        self.postprocessBtns.append(self.rawBtn)
        self.meanBtn = QPushButton('Mean')
        self.meanBtn.clicked.connect(lambda: self.SelectPostProcessOption('mean'))
        self.postprocessBtns.append(self.meanBtn)
        self.stddevBtn = QPushButton('Std Dev')
        self.stddevBtn.clicked.connect(lambda: self.SelectPostProcessOption('stddev'))
        self.postprocessBtns.append(self.stddevBtn)
        for btn in self.postprocessBtns:
            btn.setFixedWidth(80)
        self.postprocessData.layout().addWidget(self.rawBtn, alignment = Qt.AlignLeft)
        self.postprocessData.layout().addWidget(self.meanBtn, alignment = Qt.AlignLeft)
        self.postprocessData.layout().addWidget(self.stddevBtn, alignment = Qt.AlignLeft)
        self.postprocessData.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.postprocessWidget.layout().addWidget(QLabel('POST-PROCESSING'), alignment = Qt.AlignLeft | Qt.AlignVCenter)
        self.postprocessWidget.layout().addWidget(self.postprocessData)
        self.widget.layout().addWidget(self.postprocessWidget, 4, 0, 2, 4)
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 6, 0, 1, 4)
    
    def SelectPostProcessOption(self, option: str = None):
        self.settings['postProcessOption'] = option if option is not None else self.settings['postProcessOption']
        for btn in self.postprocessBtns:
            btn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
        if self.settings['postProcessOption'] == 'raw':
            self.postProcessOptionWasChanged = True
            self.rawBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5, borderColor = '#EB9423'))
        elif self.settings['postProcessOption'] == 'mean':
            self.postProcessOptionWasChanged = True
            self.meanBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5, borderColor = '#EB9423'))
        elif self.settings['postProcessOption'] == 'stddev':
            self.postProcessOptionWasChanged = True
            self.stddevBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5, borderColor = '#EB9423'))
    
    def SelectTimeWindow(self, timeInSeconds: int = None):
        padding = 0
        self.settings['windowSizeInSeconds'] = timeInSeconds if timeInSeconds is not None else self.settings['windowSizeInSeconds']
        for btn in self.trailingBtns:
            btn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
        if self.settings['windowSizeInSeconds'] == 5:
            self.trailing5secBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5, borderColor = '#EB9423'))
            self.ax.set_xlim(0, 5 + padding)
            self.ax.set_xlabel('Trailing Time (seconds)', color = '#6e6e6e', fontsize = 4)
            self.ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        elif self.settings['windowSizeInSeconds'] == 10:
            self.trailing10secBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5, borderColor = '#EB9423'))
            self.ax.set_xlim(0, 10 + padding)
            self.ax.set_xlabel('Trailing Time (seconds)', color = '#6e6e6e', fontsize = 4)
            self.ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        elif self.settings['windowSizeInSeconds'] == 30:
            self.trailing30secBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5, borderColor = '#EB9423'))
            self.ax.set_xlim(0, 30 + padding)
            self.ax.set_xlabel('Trailing Time (seconds)', color = '#6e6e6e', fontsize = 4)
            self.ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins = 10))
        elif self.settings['windowSizeInSeconds'] == 60:
            self.trailing1minBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5, borderColor = '#EB9423'))
            self.ax.set_xlim(0, 60 + padding)
            self.ax.set_xlabel('Trailing Time (seconds)', color = '#6e6e6e', fontsize = 4)
            self.ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins = 10))
        elif self.settings['windowSizeInSeconds'] == 300:
            self.trailing5minBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5, borderColor = '#EB9423'))
            self.ax.set_xlim(0, 5 + padding)
            self.ax.set_xlabel('Trailing Time (minutes)', color = '#6e6e6e', fontsize = 4)
            self.ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        elif self.settings['windowSizeInSeconds'] == 900:
            self.trailing15minBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5, borderColor = '#EB9423'))
            self.ax.set_xlim(0, 15 + padding)
            self.ax.set_xlabel('Trailing Time (minutes)', color = '#6e6e6e', fontsize = 4)
            self.ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins = 10))
        self.canvas.draw()

    def AddLinkIn(self, ID, socket, streamTypeIn = '', updateGroupLinks = True, **kwargs):
        success = super().AddLinkIn(ID, socket, streamTypeIn, updateGroupLinks, **kwargs)
        if success:
            self.timestamp = self.Timestamp(includeDate = True, stripColons = True)
            self.data[ID] = np.nan
            line, = self.ax.plot([], [], label = shared.entities[ID].name, lw = .5)
            line.set_animated(True)  # Enable blitting for this line
            self.plotLines[ID] = line
            self.lineData[ID] = deque([])
            self.ax.legend(loc='upper right', fontsize = 3, ncols = 4, frameon = False, labelcolor = '#6e6e6e')
            self.canvas.draw()
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)
            self.canvas.blit(self.ax.bbox)
            self.saveName = f'profiler_{'_'.join([''.join(''.join('-'.join((' '.join(shared.entities[ID].name.split(':'))).split()).split('(')).split(')')) for ID in self.linksIn])}_{self.settings['postProcessOption']}_{self.timestamp}.csv'
            self.savePath = Path(shared.cwd) / 'datadump' / self.saveName
            self.data.to_csv(self.savePath, index = False)
        return success

    def RemoveLinkIn(self, ID):
        super().RemoveLinkIn(ID)
        self.plotLines[ID].remove()
        colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
        self.ax.set_prop_cycle(cycler(color = colors[len(self.plotLines) - 1:]))
        self.plotLines.pop(ID)
        self.data.drop(columns = [ID], inplace = True)
        handles, labels = self.ax.get_legend_handles_labels()
        newHandles = [h for h, l in zip(handles, labels) if l != shared.entities[ID].name]
        newLabels = [l for l in labels if l != shared.entities[ID].name]
        self.ax.legend(newHandles, newLabels, loc='upper right', fontsize = 3, ncols = 4, frameon = False, labelcolor = '#6e6e6e')
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
    
    def FetchValues(self):
        while True:
            nowTime = time.time()
            if self.stopCheckThread.wait(timeout = self.pollPeriod):
                break
            if len(self.linksIn) == 0:
                continue
            newData = {}
            newData['timestamp'] = nowTime
            for ID in self.linksIn:
                newData[ID] = shared.entities[ID].Start()
                # newData[ID] = np.random.randn() * ID
            newData = pd.DataFrame([newData])
            self.data = pd.concat([self.data, newData], ignore_index = True)
            self.data = self.data[nowTime - self.data['timestamp'] <= self.settings['windowSizeInSeconds']].reset_index(drop = True)
            self.updatePlotSignal.emit()

    def BaseStyling(self):
        super().BaseStyling()
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontColor = '#c4c4c4', borderRadiusBottomLeft = 8, borderRadiusBottomRight = 8, borderRadiusTopLeft = 0, borderRadiusTopRight = 0))
            self.title.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))
            self.trailing5secBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
            self.trailing10secBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
            self.trailing30secBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
            self.trailing1minBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
            self.trailing5minBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
            self.trailing15minBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
            self.rawBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
            self.meanBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))
            self.stddevBtn.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', fontColor = '#c4c4c4', borderRadius = 5))