from PySide6.QtWidgets import QWidget, QListWidgetItem, QCompleter, QLineEdit, QPushButton, QLabel, QVBoxLayout, QSpacerItem, QSizePolicy, QHBoxLayout
from PySide6.QtCore import Qt, QStringListModel
from .component import Component
from ..blocks.draggable import Draggable
from ..blocks.pv import PV
from ..expandable import Expandable
from .. import shared
from .. import style

# class KernelComponent(QWidget):
class KernelComponent(Component):
    def __init__(self, pv, component, expandable = None, **kwargs):
        super().__init__(pv, component, expandable, **kwargs)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(10, 5, 10, 10)
        self.layout().setSpacing(5)
        self.displayHeight = 0
        self.completer = QCompleter()
        self.completer.setModel(QStringListModel([f'{shared.entities[pID].name} (ID: {shared.entities[pID].ID})' for pID in shared.PVIDs]))
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        # Automatic status
        description = QLabel(f'(<span style = "color: #308dc2">?</span>) An automatic kernel acts over all dimensions, whereas manual is over a user-defined subset.')
        description.setWordWrap(True)
        description.setFixedHeight(50)
        self.layout().addWidget(description)
        mode = 'Auto' if self.pv.automatic else 'Manual'
        if self.expandable is not None:
            self.expandable.header.setText(f'{self.expandable.header.text()} ({mode})')
        self.switch = QPushButton(f'Switch')
        self.switch.setFixedSize(65, 30)
        self.switch.pressed.connect(self.SwitchMode)
        self.layout().addWidget(self.switch)
        self.layout().addItem(QSpacerItem(0, 10, QSizePolicy.Expanding, QSizePolicy.Preferred))
        if not self.pv.automatic:
            # Text search
            self.searchWidget = QWidget()
            self.searchWidget.setFixedHeight(30)
            self.searchWidget.setLayout(QHBoxLayout())
            self.searchWidget.layout().setContentsMargins(0, 0, 0, 0)
            self.searchWidget.layout().setSpacing(2)
            self.search = QLineEdit()
            self.search.setFixedWidth(200)
            self.search.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            self.search.setAlignment(Qt.AlignVCenter)
            self.search.setPlaceholderText('Search PVs ...')
            self.search.setCompleter(self.completer)
            # editor select button
            self.editorSelect = QPushButton('Hand Pick')
            self.editorSelect.setFixedWidth(100)
            self.editorSelect.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            self.editorSelect.pressed.connect(self.EditorSelect)
            self.searchWidget.layout().addWidget(self.search)
            self.searchWidget.layout().addWidget(self.editorSelect, alignment = Qt.AlignRight)
            self.layout().addWidget(self.searchWidget)
            # list of attached PVs
            linkedPVs = self.pv.settings['linkedPVs']
            for ID in linkedPVs:
                widget = QWidget()
                widget.setLayout(QHBoxLayout())
                widget.layout().setContentsMargins(0, 0, 0, 0)
                widget.layout().setSpacing(2)
                label = QLabel(f'{shared.entities[ID].name} (ID: {shared.entities[ID].ID})')
                optimisationLowerLimit = QLineEdit(f'{shared.entities[ID].settings['components']['value']['min']:.3f}')
                optimisationLowerLimit.setFixedWidth(75)
                optimisationLowerLimit.setAlignment(Qt.AlignCenter)
                optimisationLowerLimit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', borderRadius = 4))
                widget.layout().addWidget(label)
                widget.layout().addWidget(optimisationLowerLimit)
                toLabel = QLabel('  to  ')
                toLabel.setAlignment(Qt.AlignCenter)
                toLabel.setStyleSheet(style.LabelStyle(color = '#2e2e2e', fontColor = '#c4c4c4'))
                widget.layout().addWidget(toLabel)
                optimisationUpperLimit = QLineEdit(f'{shared.entities[ID].settings['components']['value']['max']:.3f}')
                optimisationUpperLimit.setFixedWidth(75)
                optimisationUpperLimit.setAlignment(Qt.AlignCenter)
                optimisationUpperLimit.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', fontColor = '#c4c4c4', borderRadius = 4))
                widget.layout().addWidget(optimisationUpperLimit)
                self.layout().addWidget(widget)

        self.UpdateColors()

    def SwitchMode(self):
        self.pv.automatic = not self.pv.automatic
        item = QListWidgetItem()
        expandable = Expandable(shared.inspector.main, item, 'Dimensions', self.pv, 'dimensions')
        expandable.ToggleContent()
        item.setSizeHint(expandable.sizeHint())
        row = shared.inspector.main.row(shared.inspector.items['dimensions'])
        shared.inspector.main.takeItem(row)
        shared.inspector.main.insertItem(row, item)
        shared.inspector.main.setItemWidget(item, expandable)
        shared.inspector.items['dimensions'] = item
        shared.inspector.expandables['dimensions'] = expandable

    def EditorSelect(self):
        shared.editorSelectMode = not shared.editorSelectMode
        if shared.editorSelectMode:
            shared.activeEditor.setStyleSheet(style.WidgetStyle(color = "#0F3A68"))
            for ID in shared.entities:
                entity = shared.entities[ID]
                if isinstance(entity, Draggable):
                    if isinstance(entity, PV):
                        entity.widget.setStyleSheet(style.WidgetStyle(color = "#1157A1", fontColor = '#c4c4c4', borderRadius = 12, marginRight = 0, fontSize = 16))
                        entity.indicator.setStyleSheet(style.IndicatorStyle(8, color = "#E0A159", borderColor = "#E7902D"))
        else:
            shared.activeEditor.setStyleSheet(style.WidgetStyle(color = "#1a1a1a"))
            for ID in shared.entities:
                entity = shared.entities[ID]
                if isinstance(entity, Draggable):
                    if isinstance(entity, PV):
                        entity.widget.setStyleSheet(style.WidgetStyle(color = "#2e2e2e", fontColor = '#c4c4c4', borderRadius = 12, marginRight = 0, fontSize = 16))
                        entity.indicator.setStyleSheet(style.IndicatorStyle(8, color = "#E0A159", borderColor = "#E7902D"))

    def UpdateColors(self):
        self.switch.setStyleSheet(style.PushButtonBorderlessStyle(color = '#2e2e2e', fontColor = '#c4c4c4'))
        if hasattr(self, 'search'):
            self.search.setStyleSheet(style.LineEditStyle(color = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.editorSelect.setStyleSheet(style.PushButtonBorderlessStyle(color = '#2e2e2e', fontColor = '#c4c4c4', marginTop = 0, marginBottom = 0, paddingLeft = 0, paddingRight = 0))