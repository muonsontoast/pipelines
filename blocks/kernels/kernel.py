from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget, QSpacerItem
from PySide6.QtCore import Qt
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
mplstyle.use('fast')
from ..draggable import Draggable
from ...clickablewidget import ClickableWidget
from ... import shared
from ..socket import Socket
from ... import style

plt.rcParams['text.usetex'] = True
plt.rcParams['font.size'] = 14

class Kernel(Draggable):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        super().__init__(
            proxy,
            name = kwargs.pop('name', 'Kernel'),
            type = kwargs.pop('type', 'Kernel'),
            size = kwargs.pop('size', [320, 275]),
            fontsize = kwargs.pop('fontsize', 12),
            # kernel-specific hyperparameters
            hyperparameters = kwargs.pop('hyperparameters', dict()),
            **kwargs
        )
        for k, val in self.settings['hyperparameters'].items():
            if val['type'] == 'vec':
                if type(val['value']) == list and val['value'] == []:
                    self.settings['hyperparameters'][k]['value'] = np.nan
        self.parent = parent
        self.widgetStyle = style.WidgetStyle(color = '#2e2e2e', borderRadius = 12, marginRight = 0, fontSize = 16)
        self.widgetSelectedStyle = style.WidgetStyle(color = "#484848", borderRadius = 12, marginRight = 0, fontSize = 16)
        # force a PV's scalar output to be shared at instantiation so modifications are seen by all connected blocks
        self.CreateEmptySharedData(np.zeros(2)) # a SET value and a READ value
        self.data[:] = np.nan
        # store the shared memory name and attrs which get copied across instances
        self.dataSharedMemoryName = self.dataSharedMemory.name
        self.dataSharedMemoryShape = self.data.shape
        self.dataSharedMemoryDType = self.data.dtype
        self.Push()

    def k(self, X1, X2):
        '''To be overriden by all subclasses inheriting from this base class.'''
        pass

    def Push(self):
        self.clickable = ClickableWidget(self)
        self.clickable.setLayout(QVBoxLayout())
        self.clickable.layout().setContentsMargins(0, 0, 0, 0)
        self.clickable.setObjectName('Kernel')
        self.widget = QWidget()
        self.widget.setObjectName('kernelHousing')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QGridLayout())
        self.widget.layout().setContentsMargins(5, 5, 5, 5)
        self.widget.layout().setSpacing(5)
        self.header = QWidget()
        self.header.setLayout(QHBoxLayout())
        self.header.layout().setContentsMargins(5, 0, 5, 0)
        self.title = QLabel(self.name, alignment = Qt.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setObjectName('title')
        self.header.layout().addWidget(self.title, alignment = Qt.AlignCenter)
        self.widget.layout().addWidget(self.header, 0, 0, 1, 3)
        # setup figure
        self.figure = Figure(figsize = (8, 8), dpi = 100)
        self.figure.subplots_adjust(left = .015, right = .985, top = .985, bottom = .015)
        self.figure.set_facecolor('none')
        self.ax = self.figure.add_subplot(111)
        self.ax.set_aspect('equal')
        self.ax.set_xticklabels([])
        self.ax.set_xticks([])
        self.ax.set_yticklabels([])
        self.ax.set_yticks([])
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.canvas.setStyleSheet('background: transparent')
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.layout().addWidget(self.canvas, 1, 0, 1, 3)
        self.clickable.layout().addWidget(self.widget)
        self.outSocket = Socket(self, 'M', 50, 25, 'right', 'out')
        self.outSocket.setFixedHeight(65)
        self.mainWidget = QWidget()
        self.mainWidget.setLayout(QGridLayout())
        self.mainWidget.layout().setSpacing(1)
        self.mainWidget.layout().setContentsMargins(0, 0, 0, 0)
        self.mainWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout().addWidget(self.mainWidget)
        marginLeft = QWidget()
        marginLeft.setFixedWidth(15)
        self.mainWidget.layout().addWidget(marginLeft, 0, 0, 3, 1)
        self.mainWidget.layout().addWidget(self.clickable, 0, 1, 3, 3)
        self.mainWidget.layout().addWidget(self.outSocket, 0, 4, 3, 1)
        self.DrawHyperparameterControls()
        self.ToggleStyling(active = False)

    def DrawHyperparameterControls(self):
        rowIdx = 3
        for k, v in self.settings['hyperparameters'].items():
            if v['type'] in ['int', 'float']:
                pass
            elif v['type'] == 'vec':
                numEdits = 0
                numEditName = f'{k}NumEdits'
                setattr(self, numEditName, 0)
                widgetName = f'{k}Widget'
                setattr(self, widgetName, QWidget())
                widget = getattr(self, widgetName)
                widget.setLayout(QHBoxLayout())
                widget.layout().setContentsMargins(0, 5, 0, 5)
                widget.setFixedHeight(40)
                housingName = f'{k}Housing'
                setattr(self, housingName, QWidget())
                housing = getattr(self, housingName)
                housing.setLayout(QHBoxLayout())
                housing.layout().setContentsMargins(2, 0, 2, 0)
                housing.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                labelHousing = QWidget()
                labelHousing.setLayout(QHBoxLayout())
                labelHousing.layout().setContentsMargins(5, 5, 5, 5)
                label = QLabel(f'{k.upper()}', alignment = Qt.AlignVCenter)
                label.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', padding = 0, fontSize = 12))
                labelHousing.layout().addWidget(label, alignment = Qt.AlignLeft)
                housing.layout().addWidget(labelHousing, alignment = Qt.AlignLeft)
                editName = f'{k}Edit0'
                if not np.isnan(v['value']):
                    for idx, val in enumerate(v['value']):
                        setattr(self, editName, QLineEdit(f'{val:.1f}'))
                        edit = getattr(self, editName)
                        edit.setStyleSheet(style.LineEditStyle(color = '#2e2e2e', fontColor = '#c4c4c4', borderRadius = 4, fontSize = 12))
                        housing.layout().addWidget(edit, alignment = Qt.AlignRight)
                        editName = f'{k}Edit{idx + 1}'
                        numEdits += 1
                else:
                    setattr(self, editName, QLineEdit('1.0'))
                    edit = getattr(self, editName)
                    edit.setStyleSheet(style.LineEditStyle(color = '#2e2e2e', borderRadius = 4, fontSize = 12))
                    housing.layout().addWidget(edit, alignment = Qt.AlignRight)
                    numEdits += 1
                setattr(self, numEditName, numEdits)
                edit.setFixedSize(40, 30)
                edit.setAlignment(Qt.AlignCenter)
                edit.returnPressed.connect(lambda name = housingName, e = edit: self.ChangeEditValue(name, e))
                # add/remove buttons
                addButton = QPushButton('+')
                addButton.setFixedSize(30, 30)
                addButton.setStyleSheet(style.PushButtonBorderlessStyle(color = '#3e3e3e', hoverColor = '#4e4e4e', fontColor = '#c4c4c4', paddingLeft = 1, paddingRight = 1,borderRadius = 4, fontSize = 12))
                addButton.clicked.connect(lambda: self.AddEdit(k))
                widget.layout().addWidget(addButton, alignment = Qt.AlignRight | Qt.AlignVCenter)
                removeButton = QPushButton('-')
                removeButton.setFixedSize(30, 30)
                removeButton.setStyleSheet(style.PushButtonBorderlessStyle(color = '#3e3e3e', hoverColor = '#4e4e4e', fontColor = '#c4c4c4', paddingLeft = 1, paddingRight = 1,borderRadius = 4, fontSize = 12))
                removeButton.clicked.connect(lambda: self.RemoveEdit(k))
                widget.layout().addWidget(removeButton, alignment = Qt.AlignRight | Qt.AlignVCenter)
                widget.layout().addWidget(housing, alignment = Qt.AlignVCenter)
                self.mainWidget.layout().addWidget(widget, rowIdx, 0, 1, 5)
            rowIdx += 1

    def AddEdit(self, hyperparameterName):
        numEdits = getattr(self, f'{hyperparameterName}NumEdits')
        setattr(self, f'{hyperparameterName}NumEdits', numEdits + 1)
        widget = getattr(self, f'{hyperparameterName}Widget')
        for idx in range(numEdits):
            editName = f'{hyperparameterName}Edit{idx}'
            widget.layout().removeWidget(getattr(self, editName))
            getattr(self, editName).deleteLater()
        numEdits += 1
        for idx in range(numEdits):
            editName = f'{hyperparameterName}Edit{idx}'
            setattr(self, editName, QLineEdit('1.0'))
            edit = getattr(self, editName)
            edit.setStyleSheet(style.LineEditStyle(color = '#2e2e2e', borderRadius = 4, fontSize = 12))
            widget.layout().addWidget(edit, alignment = Qt.AlignRight)
            edit.setFixedSize(40, 30)
            edit.setAlignment(Qt.AlignCenter)
            edit.returnPressed.connect(lambda name = f'{hyperparameterName}Housing', e = edit: self.ChangeEditValue(name, e))

    def RemoveEdit(self, hyperparameterName):
        numEdits = getattr(self, f'{hyperparameterName}NumEdits')
        if numEdits == 0:
            return
        numEdits -= 1
        widget = getattr(self, f'{hyperparameterName}Edit{numEdits}')
        getattr(self, f'{hyperparameterName}Widget').layout().removeWidget(widget)
        widget.deleteLater()
        setattr(self, f'{hyperparameterName}NumEdits', numEdits)

    def ChangeEditValue(self, name, edit):
        val = edit.text()
        try:
            val = float(val)
        except:
            return
        getattr(self, name).layout().removeWidget(edit)
        edit.deleteLater()
        newEdit = QLineEdit(f'{val:.1f}')
        newEdit.setStyleSheet(style.LineEditStyle(color = '#2e2e2e', borderRadius = 4, fontSize = 12))
        newEdit.setFixedSize(40, 30)
        newEdit.setAlignment(Qt.AlignCenter)
        newEdit.returnPressed.connect(lambda name = name, e = newEdit: self.ChangeEditValue(name, e))
        getattr(self, name).layout().addWidget(newEdit, alignment = Qt.AlignRight)

    def mouseReleaseEvent(self, event):
        # Store temporary values since Draggable overwrites them in its mouseReleaseEvent override.
        isActive = self.active
        hasCursorMoved = self.cursorMoved
        canDrag = self.canDrag
        super().mouseReleaseEvent(event)
        if not canDrag:
            return
        if not hasCursorMoved:
            # Draggable mouse release event gets called after this PV mouse release event so the shared.selectedPV has not been set yet.
            if not isActive:
                shared.inspector.Push(self)
            else:
                shared.inspector.Push()

    def BaseStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(self.widgetStyle)
            self.header.setStyleSheet(style.WidgetStyle(color = 'none'))
            self.title.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))
            self.outSocket.setStyleSheet(style.WidgetStyle(marginLeft = 2))

    def SelectedStyling(self):
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(self.widgetSelectedStyle)
            self.header.setStyleSheet(style.WidgetStyle(color = 'none'))
            self.title.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))
            self.outSocket.setStyleSheet(style.WidgetStyle(marginLeft = 2))

    def ClearLayout(self):
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()