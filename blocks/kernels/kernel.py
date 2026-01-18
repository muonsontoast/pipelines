from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QLineEdit, QGraphicsProxyWidget, QMenu
from PySide6.QtCore import Qt, QPointF
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
mplstyle.use('fast')
import asyncio
from ..draggable import Draggable
from ...components.kernel import KernelComponent
from ...clickablewidget import ClickableWidget
from ... import shared
from ..socket import Socket
from ...ui.kernelmenu import KernelMenu
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
            size = kwargs.pop('size', [300, 275]),
            fontsize = kwargs.pop('fontsize', 12),
            headerColor = '#3e3e3e',
            # kernel-specific hyperparameters
            hyperparameters = kwargs.pop('hyperparameters', dict()),
            components = {
                'dimensions': dict(name = 'Dimensions', type = KernelComponent),
            },
            linkedPVs = dict(),
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

        if self.__class__ != Kernel: # only Push immediately if not a base class instance.
            self.Push()

    async def k(self, X1, X2):
        '''To be overriden by all subclasses inheriting from this base class.'''
        pass

    def ShowMenu(self, context):
        if shared.kernelMenu is not None:
            if shared.kernelMenu != self.kernelMenu or self.kernelMenu.currentHyperparameter != context.correspondingHyperparameter:
                shared.kernelMenu.Hide()
                shared.kernelMenu.draggable.kernelMenuIsOpen = False
                shared.kernelContext.setText('+')
        localPos = context.mapTo(self.proxy.widget(), QPointF(40, -20))
        finalPos = self.proxy.scenePos() + localPos
        self.kernelMenu.currentHyperparameter = context.correspondingHyperparameter
        self.kernelMenu.Show(finalPos)
        shared.kernelMenu = self.kernelMenu
        shared.kernelContext = context
        context.setText('-')
        self.kernelMenuIsOpen = True
        # show all the values for this hyperparameter
        iters = 1 if type(self.settings['hyperparameters'][context.correspondingHyperparameter]['value']) in [int, float] else self.settings['hyperparameters'][context.correspondingHyperparameter]['value'].shape[0]
        iterable = self.settings['hyperparameters'][context.correspondingHyperparameter]['value']
        iterable = np.array([iterable]) if type(iterable) in [int, float] else iterable
        for idx in range(iters):
            widget = QWidget()
            widget.setFixedHeight(40)
            widget.setLayout(QHBoxLayout())
            widget.setContentsMargins(0, 0, 0, 0)
            label = QLabel(f'Dim {idx}')
            widget.layout().addWidget(label, alignment = Qt.AlignLeft)
            edit = QLineEdit(f'{iterable[idx]:2f}')
            edit.setAlignment(Qt.AlignCenter)
            edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            edit.setStyleSheet(style.LineEditStyle(fontColor = '#c4c4c4', color = '#2e2e2e'))
            widget.layout().addWidget(edit)
            copy = QPushButton('CP')
            copy.setStyleSheet(style.PushButtonBorderlessStyle(color = '#2e2e2e', fontColor = '#c4c4c4', fontSize = 12))
            copy.setFixedSize(20, 20)
            widget.layout().addWidget(copy, alignment = Qt.AlignVCenter)
            delete = QPushButton('Del')
            delete.setStyleSheet(style.PushButtonBorderlessStyle(color = '#2e2e2e', fontColor = '#c4c4c4', fontSize = 12))
            delete.setFixedSize(20, 20)
            widget.layout().addWidget(delete, alignment = Qt.AlignVCenter)
            self.kernelMenu.body.layout().insertWidget(idx, widget)

    def CloseMenu(self, context):
        if shared.kernelMenu == self.kernelMenu:
            self.kernelMenu.Hide()
            self.kernelMenu.currentHyperparameter = None
            shared.kernelMenu = None
            shared.kernelContext = None
        context.setText('+')
        self.kernelMenuIsOpen = False

    def ToggleMenu(self, context):
        if not self.kernelMenuIsOpen:
            self.ShowMenu(context)
            return
        if context.correspondingHyperparameter != self.kernelMenu.currentHyperparameter:
            self.ShowMenu(context)
            return
        self.CloseMenu(context)

    def Push(self):
        super().Push()
        self.widget = QWidget()
        self.main.layout().addWidget(self.widget)
        self.widget.setObjectName('kernelHousing')
        self.widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.setLayout(QGridLayout())
        self.widget.layout().setContentsMargins(5, 5, 5, 5)
        self.widget.layout().setSpacing(5)
        # setup figure
        self.figure = Figure(figsize = (8, 8), dpi = 100)
        self.figure.subplots_adjust(left = .015, right = .985, top = .985, bottom = .015)
        self.figure.set_facecolor('none')
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.canvas.setStyleSheet('background: transparent')
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.widget.layout().addWidget(self.canvas, 1, 0, 1, 3)
        self.AddSocket('out', 'M')
        self.DrawHyperparameterControls()
        self.kernelMenu = KernelMenu(self)
        setattr(self.kernelMenu, 'draggable', self)
        self.kernelMenu.canDrag = False
        self.kernelMenu.Hide()
        self.kernelMenuIsOpen = False
        self.automatic = True # Automatic = defined over all relevant decision vars automatically, Manual = defined over a subset of relevant decision variables (useful for some kernel compositions).
        self.UpdateFigure()
        self.ToggleStyling(active = False)

    def CheckState(self):
        pass

    def ClearFigure(self):
        self.ax.clear()
        self.ax.set_aspect('equal')
        self.ax.set_xticklabels([])
        self.ax.set_xticks([])
        self.ax.set_yticklabels([])
        self.ax.set_yticks([])

    async def DrawFigure(self, ignoreDraw = False):
        x = np.linspace(-5, 5, 40)
        x = x[..., np.newaxis]
        y = np.linspace(-5, 5, 40)
        y = y[..., np.newaxis]
        Z = await self.k(x, y)
        if not ignoreDraw:
            im = self.ax.imshow(Z, origin = 'lower', cmap = 'viridis')
        return Z
    
    async def DrawAndRefresh(self):
        await self.DrawFigure()
        self.canvas.draw()

    def UpdateFigure(self):
        self.ClearFigure()
        asyncio.create_task(self.DrawAndRefresh())

    def DrawHyperparameterControls(self):
        rowIdx = 3
        for k, v in self.settings['hyperparameters'].items():
            numEdits = 0
            numEditName = f'{k}NumEdits'
            setattr(self, numEditName, 0)
            widgetName = f'{k}Widget'
            widget = QWidget()
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
            labelText = f'{k.capitalize()} (Dim 1)' if k.lower() != 'scale' else f'{k.capitalize()}'
            label = QLabel(labelText, alignment = Qt.AlignVCenter)
            label.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', padding = 0, fontSize = 12))
            labelHousing.layout().addWidget(label, alignment = Qt.AlignLeft)
            housing.layout().addWidget(labelHousing, alignment = Qt.AlignLeft)
            editName = f'{k}Edit'
            setattr(self, widgetName, QWidget())
            rightInnerHousing = getattr(self, widgetName)
            rightInnerHousing.setLayout(QHBoxLayout())
            rightInnerHousing.layout().setContentsMargins(0, 0, 0, 0)
            rightInnerHousing.layout().setSpacing(5)
            setattr(self, editName, QLineEdit('1.00'))
            edit = getattr(self, editName)
            edit.setStyleSheet(style.LineEditStyle(color = '#2e2e2e', borderRadius = 4, fontSize = 12))
            rightInnerHousing.layout().addWidget(edit, alignment = Qt.AlignRight)
            numEdits += 1
            setattr(self, numEditName, numEdits)
            edit.setFixedSize(60, 30)
            edit.setAlignment(Qt.AlignCenter)
            edit.returnPressed.connect(lambda name = widgetName, e = edit: self.ChangeEditValue(name, e))
            if v['type'] == 'vec':
                context = QPushButton('+')
                setattr(context, 'draggable', self)
                setattr(context, 'correspondingHyperparameter', k)
                context.setFixedSize(35, 30)
                context.setStyleSheet(style.PushButtonBorderlessStyle(color = '#2e2e2e', fontColor = '#c4c4c4', fontSize = 16))
                context.clicked.connect(lambda pressed, c = context: self.ToggleMenu(c))
                rightInnerHousing.layout().addWidget(context, alignment = Qt.AlignRight)
            housing.layout().addWidget(rightInnerHousing, alignment = Qt.AlignRight)
            widget.layout().addWidget(housing, alignment = Qt.AlignVCenter)
            self.main.layout().addWidget(widget)
            # self.mainWidget.layout().addWidget(widget, rowIdx, 1, 1, 3)
            rowIdx += 1

    def AddEdit(self, hyperparameterName):
        numEdits = getattr(self, f'{hyperparameterName}NumEdits')
        setattr(self, f'{hyperparameterName}NumEdits', numEdits + 1)
        widget = getattr(self, f'{hyperparameterName}Widget')
        editName = f'{hyperparameterName}Edit'
        edit = getattr(self, editName)
        editIndex = widget.layout().indexOf(edit)
        widget.layout().removeWidget(edit)
        getattr(self, editName).deleteLater()
        numEdits += 1
        editName = f'{hyperparameterName}Edit'
        setattr(self, editName, QLineEdit('1.0'))
        edit = getattr(self, editName)
        edit.setStyleSheet(style.LineEditStyle(color = '#2e2e2e', borderRadius = 4, fontSize = 12))
        widget.layout().insertWidget(editIndex, edit, alignment = Qt.AlignRight)
        edit.setFixedSize(60, 30)
        edit.setAlignment(Qt.AlignCenter)
        edit.returnPressed.connect(lambda name = f'{hyperparameterName}Housing', e = edit: self.ChangeEditValue(name, e))

    def ChangeEditValue(self, name, edit):
        val = edit.text()
        try:
            val = float(val)
        except:
            return
        widget = getattr(self, name)
        editIdx = widget.layout().indexOf(edit)
        widget.layout().removeWidget(edit)
        edit.deleteLater()
        newEdit = QLineEdit(f'{val:.2f}')
        newEdit.setStyleSheet(style.LineEditStyle(color = '#2e2e2e', borderRadius = 4, fontSize = 12))
        newEdit.setFixedSize(60, 30)
        newEdit.setAlignment(Qt.AlignCenter)
        newEdit.returnPressed.connect(lambda name = name, e = newEdit: self.ChangeEditValue(name, e))
        widget.layout().insertWidget(editIdx, newEdit, alignment = Qt.AlignRight)
        self.settings['hyperparameters'][name.split('Widget')[0]]['value'] = float(edit.text())
        self.UpdateFigure()
        # trigger updates in any downstream blocks attached to this that display visual information.
        for ID in self.linksOut:
            if callable(getattr(shared.entities[ID], 'UpdateFigure', None)):
                shared.entities[ID].UpdateFigure()

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
        super().BaseStyling()
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontColor = '#c4c4c4', borderRadiusBottomLeft = 8, borderRadiusBottomRight = 8, borderRadiusTopLeft = 0, borderRadiusTopRight = 0))
            self.title.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))
            self.outSocket.setStyleSheet(style.WidgetStyle(marginLeft = 2))

    def SelectedStyling(self):
        super().SelectedStyling()
        if shared.lightModeOn:
            pass
        else:
            self.widget.setStyleSheet(style.WidgetStyle(color = '#3a3a3a', fontColor = '#c4c4c4', borderRadiusBottomLeft = 8, borderRadiusBottomRight = 8, borderRadiusTopLeft = 0, borderRadiusTopRight = 0))
            self.title.setStyleSheet(style.WidgetStyle(fontColor = '#c4c4c4'))
            self.outSocket.setStyleSheet(style.WidgetStyle(marginLeft = 2))

    def ClearLayout(self):
        while self.layout() and self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()