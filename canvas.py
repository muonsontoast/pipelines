from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PySide6.QtWidgets import (
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal

class Canvas(FigureCanvas):
    elementClicked = Signal(str)

    def __init__(self, parent = None, width = 5, height = 4, dpi = 100, **kwargs):
        self.fig = Figure(figsize = (width, height), dpi = dpi, constrained_layout = True, facecolor = 'none')
        super().__init__(self.fig)
        self.axes = [None] * 3
        self.axes[0] = self.fig.add_subplot(111)    
        self.setParent(parent)
        self.setStyleSheet("background-color: transparent;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        self.mpl_connect('pick_event', self.onPick)
        self.axes[0].grid(alpha = .35, which = 'both') if kwargs.get('grid', False) else None
        self.axes[0].minorticks_on() if kwargs.get('minorticks', False) else None
        yticks = kwargs.get('yticks', [])
        self.axes[0].set_yticks(yticks)
        ytickLabels = kwargs.get('ytickLabels', [])
        self.axes[0].set_yticklabels(ytickLabels)
        yLabel = kwargs.get('yLabel', '')
        self.axes[0].set_ylabel(yLabel)
        xticks = kwargs.get('xticks', [])
        self.axes[0].set_xticks(xticks)
        xtickLabels = kwargs.get('xtickLabels', [])
        self.axes[0].set_xticklabels(xtickLabels)
        xLabel = kwargs.get('xLabel', '')
        self.axes[0].set_xlabel(xLabel)

    def onPick(self, event):
        '''This method triggers for any click in the canvas so checks must be done.'''
        elementName = event.artist.get_gid()
        if elementName:
            self.elementClicked.emit(elementName)

    def clear(self):
        self.ax.clear()
        self.ax.set_xticks([])
        self.ax.set_xticklabels([])
        self.ax.set_yticks([])
        self.ax.set_yticklabels([])
        self.draw()