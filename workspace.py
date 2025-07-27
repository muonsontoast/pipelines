from PySide6.QtWidgets import (
    QPushButton, QTabWidget, QMenu, QStackedLayout, QSizePolicy, QLabel
)
from PySide6.QtCore import QPoint
from .monitor import Monitor
from .controlpanel import ControlPanel
from .utils.entity import Entity
from . import editor
from . import style
from . import shared

class Workspace(Entity, QTabWidget):
    '''Main editor window for user interaction.'''
    def __init__(self, parent):
        super().__init__(name = 'Workspace', type = Workspace)
        self.parent = parent
        self.setLayout(QStackedLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        size = self.settings.get('size', (None, None))
        sizePolicy = [None, None]
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
        self.setSizePolicy(*sizePolicy)
        shared.workspace = self
        self.editors, self.monitors, self.controlPanels, self.optimisationPanels =  dict(), dict(), dict(), dict()
        self.Push()

    def Push(self):
        self.AddEditor()
        # Corner widget
        self.addButton = QPushButton('Add Window')
        self.addButton.setFixedHeight(25)
        self.menu = QMenu()
        self.UpdateColors()
        self.menu.addAction('Editor', self.AddEditor)
        self.menu.addAction('Monitor', self.AddMonitor)
        self.menu.addAction('Control Panel', self.AddControlPanel)
        self.addButton.clicked.connect(self.ShowMenu)
        self.setCornerWidget(self.addButton)

    def UpdateColors(self):
        if shared.lightModeOn:
            self.menu.setStyleSheet(style.MenuStyle(color = '#B5AB8D', hoverColor = '#D2C5A0', fontColor = '#1e1e1e'))
        else:
            self.menu.setStyleSheet(style.MenuStyle(color = '#363636', hoverColor = '#2D2D2D', fontColor = '#c4c4c4'))

    def AddEditor(self):
        editorPanel = editor.Editor(self)
        editorPanel.setStyleSheet(style.EditorStyle())
        idx = 0
        for e in self.editors.values():
            if e.settings['name'] != f'Editor ({idx})':
                break
            idx += 1
        name = f'Editor ({idx})'
        editorPanel.AssignSettings(name = name)
        # entity.AddEntity(entity.Entity(f'editor{idx}', 'GUI', entity.AssignEntityID(), widget = editor.Editor))
        # Entity(editorPanel)
        self.editors[idx] = editorPanel
        tabName = '\U0001F441\uFE0F ' + name if idx > 0 else '\U0001F441\uFE0F Editor'
        self.addTab(editorPanel, tabName)
        shared.editorOpenIdx = len(shared.editors) - 1

    def AddControlPanel(self):
        controlPanel = ControlPanel(self)
        idx = 0
        for c in self.controlPanels.values():
            if c.settings['name'] != f'Control Panel ({idx})':
                break
            idx += 1
        name = f'Control Panel ({idx})'
        controlPanel.AssignSettings(name = name)
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
        entity.AddEntity(entity.Entity(f'monitor{idx}', 'GUI', entity.AssignEntityID(), widget = Monitor))
        self.monitors[idx] = monitor
        tabName = name if idx > 0 else 'Monitor'
        self.addTab(monitor, tabName)
        shared.editors[shared.editorOpenIdx].AddWidget(QLabel('haha, I\'m embedded!'))

    def ShowMenu(self):
        position = self.addButton.mapToGlobal(QPoint(0, self.addButton.height()))
        self.menu.popup(position)