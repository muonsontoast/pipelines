from PySide6.QtWidgets import (
    QWidget, QLineEdit, QCompleter, QLabel, QPushButton,
    QGridLayout, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QStringListModel
from . import shared
from . import style
from . import lattice

class Link(QWidget):
    def __init__(self, pv, componentIdx):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(15, 0, 0, 0)
        self.pv = pv
        self.componentIdx = componentIdx
        self.linkedElement = None
        # Lattice elements and a list of names + indexes
        if shared.elements is None:
            shared.elements = lattice.GetLatticeInfo(lattice.LoadLattice(shared.latticePath))
            shared.names = [a + f' ({str(b)})' for a, b in zip(shared.elements.Name, shared.elements.Index)]
        # Completer
        self.completer = QCompleter()
        self.completer.setModel(QStringListModel(shared.names))
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        # self.completer.setFilterMode(Qt.MatchContains)
        # Text search
        self.search = QLineEdit()
        self.search.setFixedSize(250, 40)
        self.search.setAlignment(Qt.AlignVCenter)
        self.search.setPlaceholderText('Search an element ...')
        self.search.setCompleter(self.completer)
        self.search.returnPressed.connect(self.Select)
        # Update colors
        self.UpdateColors()
        # Add searcher to self
        self.layout().addWidget(self.search)

    def Select(self):
        self.search.clearFocus()
        split = self.search.text().split(' ')
        self.search.setText(split[0])
        self.linkedElement = shared.elements.iloc[int(split[1][1:-1])]

    def UpdateColors(self):
        if shared.lightModeOn:
            self.search.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 15))
        else:
            self.search.setStyleSheet(style.LineEditStyle(color = '#2d2d2d', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 15))