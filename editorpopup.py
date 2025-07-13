from PySide6.QtWidgets import (
    QWidget, QFrame, QPushButton, QLabel, QGraphicsProxyWidget,
    QGridLayout, QHBoxLayout, QSizePolicy,
    QSpacerItem,
)
from PySide6.QtCore import Qt
from . import shared
from . import style

class Popup(QGraphicsProxyWidget):
    '''Inspector popup that appears inside the editor window.'''
    def __init__(self, parent, x, y, width, height):
        '''A popup inspector inside the editor. Set `x`, `y`, `width`, `height` when instantiating.'''
        super().__init__()
        self.settings = dict()
        self.minimised = False
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.parent = parent
        self.background = QWidget(parent)
        self.background.setLayout(QGridLayout())
        self.background.layout().setContentsMargins(0, 0, 0, 0)
        # The top bar
        self.topBar = QWidget()
        self.topBar.setLayout(QHBoxLayout())
        self.topBar.layout().setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.topBar.setFixedHeight(30)
        self.objectType = QLabel('')
        self.objectType.setFixedHeight(20)
        self.objectType.setStyleSheet('padding-left: 0px;')
        self.topBar.layout().addWidget(self.objectType) # type name
        self.topBar.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred)) # Padding between the two sections of the top bar.
        self.minimiseButton = QPushButton('\u005F')
        self.minimiseButton.setStyleSheet(f'''
        background-color: #3d3d3d;
        color: #c4c4c4;
        padding: 2px;
        padding-bottom: 4px;
        border: none;
        border-radius: 0px;
        ''')
        self.minimiseButton.setFixedSize(20, 20)
        self.minimiseButton.clicked.connect(self.MinimiseOrExpandPopup)
        self.topBar.layout().addWidget(self.minimiseButton)
        # Close button
        self.closeButton = QPushButton('\u2715')
        self.closeButton.setStyleSheet(f'''
        background-color: #eb4034;
        color: #c4c4c4;
        padding: 2px;
        padding-right: 2px;
        border: none;
        border-radius: 0px;
        ''')
        self.closeButton.setFixedSize(20, 20)
        self.topBar.layout().addWidget(self.closeButton)
        self.background.layout().addWidget(self.topBar, 0, 0, 1, 4)
        # The main body
        self.body = QWidget()
        self.background.layout().addWidget(self.body, 1, 0, 1, 4) # body placeholder.
        self.separator = QWidget()
        self.separator.setStyleSheet('background-color: red')
        self.background.layout().addWidget(self.separator, 2, 0, 1, 4)
        # The button section
        self.buttons = QWidget()
        self.buttons.setLayout(QGridLayout())
        self.background.layout().addWidget(self.buttons, 3, 0, 1, 4)
        # The additional context bar at the bottom
        self.contextBar = QWidget()
        self.background.layout().addWidget(self.contextBar)
        # Set the width and height of the popup
        self.background.setFixedSize(width, height)
        # Move the popup to the correct part of the graphics view
        self.background.move(x, y)
        # Set the popup to float above the graphics view so it doesn't pan with the scene
        self.background.raise_()
        # Assign the widget to the proxy
        self.setWidget(self.background)
        # Assign popup colors
        self.UpdateColors()
        # Assign self to the shared reference
        shared.editorPopup = self

    def Push(self, settings):
        '''Update the popup.'''
        objectType = settings['type']
        if objectType == 'PV':
            objectType = 'Process Variable'
        self.objectType.setText(objectType)

    def UpdateColors(self):
        if shared.lightModeOn:
            self.background.setStyleSheet(style.EditorControlsStyle(color = '#D2C5A0', borderColor = '#B5AB8D', fontColor = '#1e1e1e'))
            self.background.setStyleSheet('background-color: #D2C5A0; padding-left: 0px; color: #1e1e1e')
        else:
            self.background.setStyleSheet(style.EditorControlsStyle(color = '#2D2D2D', borderColor = '#363636', fontColor = '#c4c4c4'))
            self.background.setStyleSheet('background-color: #2D2D2D; padding-left: 0px; color: #c4c4c4')

    def MinimiseOrExpandPopup(self):
        if self.minimised:
            self.minimiseButton.setText('\u005f')
            self.body.setVisible(True)
            self.buttons.setVisible(True)
            self.contextBar.setVisible(True)
            self.objectType.setVisible(True)
            if shared.lightModeOn:
                self.background.setStyleSheet('background-color: #D2C5A0;')
            else:
                self.background.setStyleSheet('background-color: #2D2D2D;')
            self.background.setFixedSize(self.width, self.height)
            self.background.move(self.x, self.y)
        else:
            self.minimiseButton.setText('\u2610')
            self.body.setVisible(False)
            self.buttons.setVisible(False)
            self.contextBar.setVisible(False)
            self.objectType.setVisible(False)
            self.background.setStyleSheet('background-color: transparent')
            self.background.setFixedSize(75, 30)
            self.background.move(self.x + self.width - 75, self.y)
        self.minimised = not self.minimised