from PySide6.QtWidgets import QWidget, QLabel, QSpacerItem, QGraphicsProxyWidget, QSizePolicy, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from mpl_toolkits.axes_grid1 import make_axes_locatable
from .draggable import Draggable
from .socket import Socket
from ..ui.runningcircle import RunningCircle
from .. import shared
from .. import style

plt.rcParams['text.usetex'] = True

class View(Draggable):
    '''Displays the data of arbitrary blocks.'''
    def __init__(self, parent, proxy: QGraphicsProxyWidget, fontsize = 12, **kwargs):
        super().__init__(proxy, name = kwargs.pop('name', 'View'), type = 'View', size = kwargs.pop('size', [600, 500]), **kwargs)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.parent = parent
        self.blockType = 'View'
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.active = False
        self.hovering = False
        self.startPos = None
        self.PVIn = None
        self.stream = None
        self.fontsize = fontsize
        self.runningCircle = RunningCircle()
        self.Push()

    def Push(self):
        super().Push()
        self.main = QWidget()
        self.main.setLayout(QVBoxLayout())
        self.main.layout().setContentsMargins(0, 0, 0, 0)
        self.widget = QWidget()
        self.widget.setObjectName('view')
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
        self.figure = Figure(figsize = (6.75, 4.25), dpi = 100)
        self.figure.set_facecolor('none')
        self.axes = self.figure.add_subplot(111)
        self.axes.tick_params(
            axis = 'both',
            colors = '#c4c4c4',
            which = 'both',
            labelsize = self.fontsize,
        )
        self.axes.set_facecolor('none')
        self.ToggleSpines(False)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.canvas.setStyleSheet('background: transparent')
        self.ClearCanvas()
        self.figure.tight_layout()
        self.plot.layout().addWidget(self.canvas)
        self.widget.layout().addWidget(self.plot)
        self.widget.layout().addWidget(QLabel('hahaha'))
        self.widget.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)) # for spacing
        self.main.layout().addWidget(self.widget)
        # Data socket
        self.dataSocketHousing = QWidget()
        self.dataSocketHousing.setLayout(QHBoxLayout())
        self.dataSocketHousing.layout().setContentsMargins(0, 0, 0, 0)
        self.dataSocketHousing.setFixedSize(50, 50)
        self.dataSocket = Socket(self, 'F', 50, 25, 'left', 'data', acceptableTypes = ['Orbit Response', 'BPM'])
        self.dataSocketHousing.layout().addWidget(self.dataSocket)
        self.FSocketNames.append('data')

        self.layout().addWidget(self.dataSocket)
        self.layout().addWidget(self.main)
        self.UpdateColors()

    def DrawCanvas(self, stream = 'raw', **kwargs):
        print('Drawing view block canvas.')
        if not self.PVIn:
            print('No PV input for view block. backing out.')
            return
        print('Clearing canvas')
        self.ClearCanvas()
        print('Clearing ticks and tick labels')
        self.stream = self.PVIn.streams[stream](**kwargs)
        print('Checking if data exists.')
        if not 'data' in self.stream.keys():
            return
        print('data available')
        self.ToggleSpines(True)
        self.axes.relim()
        self.axes.autoscale_view()
        xunits = f' ({self.stream['xunits']})' if self.stream['xunits'] != '' else ''
        self.axes.set_xlabel(f'{self.stream['xlabel']}{xunits}', fontsize = self.fontsize, labelpad = 10, color = '#c4c4c4')
        yunits = f' ({self.stream['yunits']})' if self.stream['yunits'] != '' else ''
        self.axes.set_ylabel(f'{self.stream['ylabel']}{yunits}', fontsize = self.fontsize, labelpad = 10, color = '#c4c4c4')
        if self.stream['plottype'] == 'imshow':
            if 'norm' in self.stream.keys():
                print('normed!')
                im = self.axes.imshow(self.stream['data'], cmap = self.stream['cmap'], norm = TwoSlopeNorm(vcenter = self.stream['vcenter']))
            else:
                im = self.axes.imshow(self.stream['data'], cmap = self.stream['cmap'])
            divider = make_axes_locatable(self.axes)
            cax = divider.append_axes("right", size = "5%", pad = 0.075)
            cb = plt.colorbar(im, cax = cax, ax = self.axes)
            cb.set_label(self.stream['cmapLabel'], rotation = 270, fontsize = self.fontsize, labelpad = 20, color = '#c4c4c4')
            cb.ax.tick_params(colors = '#c4c4c4', labelsize = self.fontsize)
        elif self.stream['plottype'] == 'plot':
            shape = self.stream['data'].shape
            dimension = len(shape)
            if dimension == 1:
                self.axes.hist(self.stream['data'], bins = kwargs.get('bins'), range = (kwargs.get('min', None), kwargs.get('max', None)))
            elif dimension == 2:
                '''Expects 2D data as 2 x n'''
                self.axes.plot(self.stream['data'][0], self.stream['data'][1], color = kwargs.get('color', 'tab:blue'), marker = 'o', markersize = 8)
        elif self.stream['plottype'] == 'scatter':
            print('Generating a scatter plot')
            shape = self.stream['data'].shape
            dimension = len(shape)
            if dimension == 1:
                print('Dimension 1')
                self.axes.hist(self.stream['data'], bins = kwargs.get('bins'), range = (kwargs.get('min', None), kwargs.get('max', None)))
            elif dimension == 2:
                '''Expects 2D data as 2 x n'''
                print('Dimension 2')
                print('shape:', self.stream['data'].shape)
                print('data:', self.stream['data'])
                print(self.stream['data'][0])
                print(self.stream['data'][1])
                self.axes.scatter(self.stream['data'][0], self.stream['data'][1], marker = 'o', s = 40)
                self.axes.minorticks_on()
                self.axes.grid(alpha = .35) if kwargs.get('grid', True) else None
            # elif dimension == 3:
            #     '''Rather than 3D points, we assume this to be a collection of lines.'''
            #     for c in range(shape[0]):
            #         self.axes.scatter(self.stream['data'][c])

        self.axes.tick_params(axis='x', which='both', labelbottom = True, length = 5)
        self.axes.tick_params(axis='y', which='both', labelleft = True, length = 5)
        self.axes.set_aspect('auto')
        self.figure.tight_layout()
        self.canvas.draw()

    def ClearCanvas(self):
        self.figure.clf()
        self.axes = self.figure.add_subplot(111)
        self.axes.tick_params(axis='x', which='both', labelbottom = False, length = 0)
        self.axes.tick_params(axis='y', which='both', labelleft = False, length = 0)
        self.axes.tick_params(
            axis = 'both',
            colors = '#c4c4c4',
            which = 'both',
            labelsize = self.fontsize,
        )
        self.axes.set_facecolor('none')
        self.ToggleSpines(False)

    def ToggleSpines(self, override: bool = None):
        for spine in self.axes.spines.values():
            spine.set_color('#c4c4c4')
            state = not spine.get_visible() if not override else override
            spine.set_visible(state)

    def UpdateColors(self):
        if not self.active:
            self.BaseStyling()
            return
        self.SelectedStyling()

    def ToggleStyling(self):
        pass

    def BaseStyling(self):
        if shared.lightModeOn:
            self.widget.setStyleSheet(f'''
            QWidget#view {{
            background-color: #D2C5A0;
            border: 2px solid #B5AB8D;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 0px;
            }}
            ''')
        else:
            "#282828"
            self.widget.setStyleSheet(f'''
            QWidget#view {{
            background-color: #2e2e2e;
            border: none;
            border-radius: 12px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 0px;
            }}
            ''')
            self.title.setStyleSheet(style.LabelStyle(padding = 0, fontSize = 18, fontColor = '#c4c4c4'))

    def SelectedStyling(self):
        if shared.lightModeOn:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #ECDAAB;
            border: 4px solid #DCC891;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            ''')
        else:
            self.widget.setStyleSheet(f'''
            QWidget#pvHousing {{
            background-color: #5C5C5C;
            border: 4px solid #424242;
            border-radius: 6px;
            font-weight: bold;
            font-size: {style.fontSize};
            font-family: {style.fontFamily};
            padding: 10px;
            }}
            ''')