from PySide6.QtWidgets import QWidget, QCompleter, QLineEdit, QLabel, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QStringListModel
from .. import shared
from .. import style

class KernelComponent(QWidget):
    def __init__(self, pv, component, **kwargs):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(10, 10, 10, 10)
        self.layout().setSpacing(10)
        self.pv = pv
        self.component = component
        self.displayHeight = 0
        self.completer = QCompleter()
        self.completer.setModel(QStringListModel([f'{shared.entities[pID].name} (ID: {shared.entities[pID].ID})' for pID in shared.PVIDs]))
        print('kernel component')
        print('PVIDs:', shared.PVIDs)
        print([f'{shared.entities[pID].name} (ID: {shared.entities[pID].ID})' for pID in shared.PVIDs])
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        # Text search
        self.search = QLineEdit()
        self.search.setFixedSize(250, 30)
        self.search.setAlignment(Qt.AlignVCenter)
        self.search.setPlaceholderText('Search PVs ...')
        self.search.setCompleter(self.completer)
        self.search.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
        # self.search.
        self.layout().addWidget(self.search)


    def UpdateColors(self):
        pass