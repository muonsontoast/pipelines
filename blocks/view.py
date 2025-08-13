from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QSpacerItem, QGraphicsProxyWidget, QSizePolicy, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.style as mplstyle
mplstyle.use('fast')
import numpy as np
from .draggable import Draggable
from .socket import Socket
from ..ui.runningcircle import RunningCircle
from ..ui.blitmanager import BlitManager
from .. import shared
from .. import style

plt.rcParams['text.usetex'] = True

class View(Draggable):
    '''Displays the data of arbitrary blocks.'''
    def __init__(self, parent, proxy: QGraphicsProxyWidget, fontsize = 12, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'View'), type = 'View', size = kwargs.pop('size', [1000, 850]), **kwargs)
        self.parent = parent
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.active = False
        self.hovering = False
        self.startPos = None
        self.stream = None
        self.fontsize = fontsize
        self.canvasHasBeenCleared = False
        self.liveUpdatesEnabled = False
        self.liveUpdateCheckFrequency = 10 # check for live data updates n times a second.
        self.liveUpdateCheckTimeInMilliseconds = 1 / self.liveUpdateCheckFrequency * 1e3
        self.runningCircle = RunningCircle()
        self.firstDraw = True
        # Attrs relevant to plotting
        self.yline = None # 1d line plots
        self.Push()

    def Push(self):
        # super().Push()
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
        header.setStyleSheet(style.WidgetStyle(color = "#7351C1", borderRadiusTopLeft = 8, borderRadiusTopRight = 8))
        header.setFixedHeight(40)
        header.setLayout(QHBoxLayout())
        header.layout().setContentsMargins(15, 0, 15, 0)
        self.title = QLabel(f'{self.settings['name']} (Disconnected)')
        header.layout().addWidget(self.title)
        # Running
        header.layout().addWidget(self.runningCircle, alignment = Qt.AlignRight)
        # Add header to layout
        self.widget.layout().addWidget(header)
        # Figure
        self.plot = QWidget()
        self.plot.setLayout(QVBoxLayout())
        self.plot.layout().setContentsMargins(15, 15, 15, 15)
        self.figure = Figure(figsize = (6.75, 7.25), dpi = 100)
        self.figure.set_facecolor('none')
        self.axes = self.figure.add_subplot(111)
        self.axes.set_aspect('auto')
        self.axes.tick_params(
            axis = 'both',
            colors = '#c4c4c4',
            which = 'both',
            labelsize = self.fontsize,
        )
        # self.axes.set_facecolor('none')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.canvas.setStyleSheet('background: transparent')
        self.plot.layout().addWidget(self.canvas)

        # live updates button
        self.liveUpdateSection = QWidget()
        self.liveUpdateSection.setLayout(QHBoxLayout())
        self.liveUpdateSection.layout().setContentsMargins(15, 15, 15, 15)
        self.liveUpdateSection.layout().addWidget(QLabel('Live Updates Enabled?'))
        self.liveButton = QPushButton('No')
        self.liveButton.setFixedSize(50, 35)
        self.liveButton.clicked.connect(self.ToggleLiveUpdates)
        self.liveUpdateSection.layout().addWidget(self.liveButton)
        self.liveUpdateSection.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.widget.layout().addWidget(self.liveUpdateSection)
        self.widget.layout().addWidget(self.plot)
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)) # for spacing
        self.main.layout().addWidget(self.widget)
        self.AddSocket('data', 'F', acceptableTypes = ['PV', 'BPM', 'Single Task GP', 'Orbit Response'])
        self.AddSocket('out', 'M')
        super().Push()
        self.ClearCanvas()
        self.ToggleSpines(False)
        self.UpdateColors()

    def CheckData(self):
        # periodically calls itself until it detects liveUpdatesEnabled is False.
        if not self.liveUpdatesEnabled:
            print('Stopping live updates')
            return
        if self.linksIn:
            self.DrawCanvas('raw')
            QTimer.singleShot(self.liveUpdateCheckTimeInMilliseconds, self.CheckData)

    def ToggleLiveUpdates(self):
        self.liveUpdatesEnabled = not self.liveUpdatesEnabled
        self.liveButton.setText('Yes') if self.liveUpdatesEnabled else self.liveButton.setText('No')
        if self.liveUpdatesEnabled:
            QTimer.singleShot(0, self.CheckData)
   
    def DrawCanvas(self, stream = 'default', **kwargs):
        if not self.linksIn:
            return
        # access stream of first linked block (may hard restrict it to one block in at some point in the future).
        self.stream = shared.entities[next(iter(self.linksIn))].streams[stream](**kwargs)
        dataShape = self.stream['data'].shape
        if dataShape == (0,):
            return
        if not self.canvasHasBeenCleared:
            self.canvasHasBeenCleared = True
            self.ClearCanvas()
            self.ToggleSpines(True)
            self.axes.tick_params(axis='x', which='both', labelbottom = True, length = 5)
            self.axes.tick_params(axis='y', which='both', labelleft = True, length = 5)
        if self.stream['plottype'] == 'imshow':
            if 'norm' in self.stream.keys():
                im = self.axes.imshow(self.stream['data'], cmap = self.stream['cmap'], norm = TwoSlopeNorm(vcenter = self.stream['vcenter']))
            else:
                im = self.axes.imshow(self.stream['data'], cmap = self.stream['cmap'])
            divider = make_axes_locatable(self.axes)
            cax = divider.append_axes("right", size = "5%", pad = 0.075)
            self.cb = self.figure.colorbar(im, cax = cax, ax = self.axes)
            self.cb.set_label(self.stream['cmapLabel'], rotation = 270, fontsize = self.fontsize, labelpad = 20, color = '#c4c4c4')
            self.cb.ax.tick_params(colors = '#c4c4c4', labelsize = self.fontsize)
            for spine in self.cb.ax.spines.values():
                spine.set_edgecolor("#c4c4c4")
                spine.set_linewidth(1)
            self.axes.set_xticks(self.stream['xticks'])
            self.axes.set_xticklabels(self.stream['xticklabels'], rotation = 90)
            self.axes.set_yticks(self.stream['yticks'])
            self.axes.set_yticklabels(self.stream['yticklabels'])
            self.axes.set_aspect('auto')
            self.figure.tight_layout()
            # testing for now ... this draw call leads to terrible performance live, need to replace with blitting.
            self.figure.canvas.draw() # I should look into whether blitting can be used to speed up 2D plots.
        # line plots
        elif self.stream['plottype'] == 'plot':
            dimension = len(dataShape)
            if dimension == 1:
                    if self.firstDraw:
                        self.axes.tick_params(axis='x', which='both', labelbottom = True, length = 5)
                        self.axes.tick_params(axis='y', which='both', labelleft = True, length = 5)
                        xunits = f' ({self.stream['xunits']})' if self.stream['xunits'] != '' else ''
                        self.axes.set_xlabel(f'{self.stream['xlabel']}{xunits}', fontsize = self.fontsize, labelpad = 10, color = '#c4c4c4')
                        yunits = f' ({self.stream['yunits']})' if self.stream['yunits'] != '' else ''
                        self.axes.set_ylabel(f'{self.stream['ylabel']}{yunits}', fontsize = self.fontsize, labelpad = 10, color = '#c4c4c4')
                        self.x = np.array(list(range(0, dataShape[0])))
                        self.ln, = self.axes.plot(self.x, self.stream['data'], color = 'tab:blue', animated = True)
                        self.axes.set_xlim(self.stream['xlim'])
                        self.axes.set_ylim(self.stream['ylim'])
                        self.axes.set_xlabel(self.stream['xlabel'])
                        self.axes.set_ylabel(self.stream['ylabel'])
                        self.axes.grid(alpha = .35)
                        self.figure.tight_layout()
                        self.firstDraw = False
                        self.figure.canvas.draw()
                        self.bm = BlitManager(self.figure.canvas, [self.ln, ])
                    else:
                        self.ln.set_ydata(self.stream['data'])
                    self.bm.update()

    def ClearCanvas(self):
        self.axes.tick_params(axis='x', which='both', labelbottom = False, length = 0)
        self.axes.tick_params(axis='y', which='both', labelleft = False, length = 0)
        self.axes.tick_params(
            axis = 'both',
            colors = '#c4c4c4',
            which = 'both',
            labelsize = self.fontsize,
        )
        self.axes.set_facecolor('none')

    def ToggleSpines(self, override: bool = None):
        for spine in self.axes.spines.values():
            spine.set_color('#c4c4c4')
            state = not spine.get_visible() if not override else override
            spine.set_visible(state)

    def AddLinkIn(self, ID, socket):
        # Allow only one block to connect to a view block at any one time.
        if self.linksIn:
            super().RemoveLinkIn(next(iter(self.linksIn)))
        super().AddLinkIn(ID, socket)
        self.title.setText('View (Connected)')

    def UpdateColors(self):
        if not self.active:
            self.BaseStyling()
            return
        self.SelectedStyling()

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 12))
            self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 18, fontColor = '#c4c4c4'))
            self.liveButton.setStyleSheet(style.PushButtonStyle(color = '#3e3e3e', hoverColor = '#4e4e4e', fontColor = '#c4c4c4'))

    def SelectedStyling(self):
        if shared.lightModeOn:
            pass
        else: 
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', borderRadius = 12))
            self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 18, fontColor = '#c4c4c4'))
            self.liveButton.setStyleSheet(style.PushButtonStyle(color = '#c4c4c4'))