from PySide6.QtWidgets import QWidget, QPushButton, QLabel, QTabWidget, QStackedLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem
from PySide6.QtCore import Qt
from ..utils.entity import Entity
from ..utils.assistant import Assistant
from .editor import Editor
from .. import style
from .. import shared

class Workspace(Entity, QTabWidget):
    '''Main editor window for user interaction.'''
    def __init__(self, parent):
        super().__init__(name = 'Workspace', type = 'Workspace')
        self.parent = parent
        self.setLayout(QStackedLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        size = self.settings.get('size', (None, None))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        shared.workspace = self
        self.editors, self.monitors, self.controlPanels, self.optimisationPanels =  dict(), dict(), dict(), dict()
        self.Push()

    def Push(self):
        self.AddEditor()
        self.assistant = Assistant(shared.activeEditor.messageTitle)
        self.assistant.Start()
        # Corner widget
        self.addButton = QPushButton('Add Window')
        self.addButton.setFixedHeight(25)
        self.UpdateColors()

    def UpdateColors(self):
        pass

    def AddEditor(self):
        editorPanel = QWidget()
        editorPanel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editorPanel.setLayout(QVBoxLayout())
        editorPanel.layout().setContentsMargins(0, 0, 0, 0)
        editorPanel.layout().setSpacing(0)
        editor = Editor(self)
        editorPanel.layout().addWidget(editor)
        editor.setStyleSheet(style.EditorStyle())
        # message
        editor.message = QWidget()
        editor.message.setStyleSheet(style.WidgetStyle(color = '#1a1a1a'))
        editor.message.setFixedHeight(35)
        editorPanel.layout().addWidget(editor.message)
        editor.message.setLayout(QHBoxLayout())
        editor.message.layout().setContentsMargins(0, 0, 5, 0)
        editor.message.layout().setSpacing(5)
        editor.messageTitle = QLabel('Assistant:')
        editor.message.layout().addWidget(editor.messageTitle, alignment = Qt.AlignLeft)
        editor.message.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        editor.message.layout().addWidget(editor.zoomTitle, alignment = Qt.AlignRight)
        # footer
        footer = QWidget()
        footer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        footer.setStyleSheet(style.WidgetStyle(color = '#1a1a1a'))
        footer.setFixedHeight(35)
        editorPanel.layout().addWidget(footer)
        footer.setLayout(QHBoxLayout())
        footer.layout().setContentsMargins(0, 0, 5, 0)
        footer.layout().setSpacing(5)
        "#e98514"
        shortcutHints = [
            f'Corrector (<span style = "color: #6e488c">Ctrl+Shift+C</span>)',
            f'BPM (<span style = "color: #6e488c">Ctrl+Shift+B</span>)',
            f'Orbit Response (<span style = "color: #6e488c">Ctrl+Shift+O</span>)',
            f'View (<span style = "color: #6e488c">Ctrl+Shift+V</span>)',
            f'Quick Menu (<span style = "color: #6e488c">Ctrl+M</span>)',
        ]
        for hint in shortcutHints:
            label = QLabel(hint)
            label.setStyleSheet(style.LabelStyle())
            footer.layout().addWidget(label, alignment = Qt.AlignLeft)
        footer.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        footer.layout().addWidget(editor.coordsTitle, alignment = Qt.AlignRight)
        idx = 0
        for e in self.editors.values():
            if e.settings['name'] != f'Editor ({idx})':
                break
            idx += 1
        name = f'Editor ({idx})'
        self.editors[idx] = editorPanel
        tabName = '\U0001F441\uFE0F ' + name if idx > 0 else 'Editor'
        self.addTab(editorPanel, tabName)
        shared.activeEditor = shared.editors[-1]