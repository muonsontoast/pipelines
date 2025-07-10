from PySide6.QtWidgets import (
    QPushButton, QTabWidget, QMenu, QStackedLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QPoint
from .monitor import Monitor
from .controlpanel import ControlPanel
from . import entity
from . import editor
from . import style
from . import shared

class Workspace(QTabWidget):
    '''Main editor window for user interaction.'''
    def __init__(self, window):
        super().__init__()
        self.parent = window
        self.setContentsMargins(0, 0, 0, 0)
        shared.workspace = self
        self.monitors, self.controlPanels, self.optimisationPanels = dict(), dict(), dict()
        self.settings = dict()
        self.Push()

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
        # Set size policy
        self.setSizePolicy(*sizePolicy)
        # A separate tab for each opened window in the editor.
        # Main editor tab
        self.editor = editor.Editor()
        shared.editor = self.editor # store the global reference.
        self.editor.setLayout(QStackedLayout())
        self.addTab(self.editor, '\U0001F441\uFE0F Editor')
        # Corner widget
        self.addButton = QPushButton('Add Window')
        self.addButton.setFixedHeight(25)
        self.addButton.setStyleSheet(style.PushButtonBorderlessStyle(marginBottom = -1))
        # self.addButton.setStyleSheet(style.PushButtonBorderlessStyle(marginBottom = -2, marginTop = -4, paddingBottom = 8, paddingTop = 10))
        self.menu = QMenu()
        if shared.lightModeOn:
            self.menu.setStyleSheet(style.MenuStyle(color = '#3C4048', hoverColor = '#303F33', fontColor = '#1c1c1c'))
        else:
            self.menu.setStyleSheet(style.MenuStyle(color = '#3C4048', hoverColor = '#303F33', fontColor = '#c4c4c4'))
        self.menu.addAction('Monitor', self.AddMonitor)
        self.menu.addAction('Control Panel', self.AddControlPanel)
        self.addButton.clicked.connect(self.ShowMenu)
        self.setCornerWidget(self.addButton)

    def AddControlPanel(self):
        controlPanel = ControlPanel(self)
        idx = 0
        for c in self.controlPanels.values():
            if c.settings['name'] != f'Control Panel ({idx})':
                break
            idx += 1
        name = f'Control Panel ({idx})'
        controlPanel.AssignSettings(name = name)
        # Add an entity
        entity.AddEntity(entity.Entity(f'controlPanel{idx}', 'GUI', entity.AssignEntityID(), widget = ControlPanel))
        self.controlPanels[idx] = controlPanel
        tabName = name if idx > 0 else 'Control Panel'
        self.addTab(controlPanel, tabName)

    def AddMonitor(self):
        monitor = Monitor(self)
        idx = 0
        for m in self.monitors.values():
            if m.settings['name'] != f'Monitor ({idx})':
                break
            idx += 1
        name = f'Monitor ({idx})'
        monitor.AssignSettings(name = name)
        # Add an entity
        entity.AddEntity(entity.Entity(f'monitor{idx}', 'GUI', entity.AssignEntityID(), widget = Monitor))
        self.monitors[idx] = monitor
        tabName = name if idx > 0 else 'Monitor'
        self.addTab(monitor, tabName)

    def ShowMenu(self):
        position = self.addButton.mapToGlobal(QPoint(0, self.addButton.height()))
        self.menu.popup(position)