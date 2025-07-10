from PySide6.QtWidgets import (
    QWidget, QLabel, QListWidget,
    QGridLayout, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from .settings import CreateSettingElement
from .scan import Scanner
from .verticalLabel import VerticalLabel
from .canvas import Canvas
from .font import SetFontSize
from . import style

class Monitor(QWidget):
    def __init__(self, window):
        super().__init__()
        self.parent = window
        self.setLayout(QGridLayout())
        self.layout().setContentsMargins(5, 20, 5, 5)
        self.setStyleSheet(style.WidgetStyle())
        self.settings = dict()
        self.Push()

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings
    
    def Push(self):
        # Set the size
        size = self.settings.get('size', (None, None))
        sizePolicy = [None, None]
        # Set horizontal
        if size[0] is None:
            sizePolicy[0] = QSizePolicy.Expanding
        else:
            self.setFixedWidth(size[0])
            sizePolicy[0] = QSizePolicy.Preferred
        # Set vertical
        if size[1] is None:
            sizePolicy[1] = QSizePolicy.Expanding
        else:
            self.setFixedHeight(size[1])
            sizePolicy[1] = QSizePolicy.Preferred
        # Set size policy.
        self.setSizePolicy(*sizePolicy)
        # Define the plot.
        self.canvasWidget = QWidget()
        self.canvasWidget.setLayout(QHBoxLayout())
        self.canvasWidget.setContentsMargins(-10, -10, -10, -10)
        self.canvasWidget.setFixedSize(400, 400)
        self.canvas = Canvas(self, 10, 10)
        self.canvasWidget.layout().addWidget(self.canvas)
        # Colorbar section
        self.colorBarWidget = QWidget()
        self.colorBarWidget.setFixedWidth(40)
        self.layout().addWidget(self.colorBarWidget, 1, 4, 2, 1)
        # Title section
        title = QLabel('Live Output:')
        title.setAlignment(Qt.AlignCenter)
        SetFontSize(title, 18)
        self.layout().addWidget(title, 0, 5, 1, 2)
        yLabel = VerticalLabel('Y')
        yLabel.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(yLabel, 1, 7, 2, 1)
        # X Label
        xLabel = QLabel('X')
        xLabel.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(xLabel, 3, 5, 1, 2)
        self.layout().addWidget(self.canvasWidget, 1, 5, 2, 2)
        self.layout().addWidget(QWidget(), 4, 0, 1, 8)
        # Left menu
        self.leftMenu = QListWidget()
        self.leftMenu.setWordWrap(True)
        self.leftMenu.setStyleSheet(style.ListWidgetStyle())
        self.layout().addWidget(self.leftMenu, 2, 0, 2, 2)
        # Right menu
        self.rightMenu = QListWidget()
        self.rightMenu.setWordWrap(True)
        self.rightMenu.setStyleSheet(style.ListWidgetStyle())
        self.layout().addWidget(self.rightMenu, 2, 2, 2, 2)
        # Define the statistics canvas section
        statisticsHousing = QWidget()
        statisticsHousing.setLayout(QGridLayout())
        statisticsHousing.layout().setSpacing(5)
        statisticsCanvas = Canvas(self, 3.5, 3)
        statisticsHousing.layout().addWidget(statisticsCanvas, 0, 0)
        # Plot x label
        statisticsHousing.layout().addWidget(QWidget(), 1, 0)
        # Plot y label
        statisticsHousing.layout().addWidget(QWidget(), 0, 1)
        self.layout().addWidget(statisticsHousing, 0, 2, 2, 2)
        # Options widget
        self.layout().addWidget(QWidget(), 0, 0, 2, 2)