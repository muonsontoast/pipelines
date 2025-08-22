from PySide6.QtWidgets import QWidget, QLineEdit, QCompleter, QLabel, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QStringListModel
from .. import shared
from .. import style
from ..lattice import latticeutils

class LinkComponent(QWidget):
    def __init__(self, pv, component):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(10, 10, 0, 0)
        self.layout().setSpacing(10)
        self.pv = pv
        self.component = component
        self.linkedElement = None
        self.displayHeight = 0
        self.pvHasLinkedElement = 'linkedElement' in self.pv.settings.keys()
        # Lattice elements and a list of names + indexes
        if shared.elements is None:
            shared.lattice = latticeutils.LoadLattice(shared.latticePath)
            shared.elements = latticeutils.GetLatticeInfo(shared.lattice)
            shared.names = [a + f' [{shared.elements.Type[b]}] ({str(b)})' for a, b in zip(shared.elements.Name, shared.elements.Index)]
        # Completer
        self.completer = QCompleter()
        self.completer.setModel(QStringListModel(shared.names))
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        # Text search
        self.search = QLineEdit()
        self.search.setFixedSize(250, 30)
        self.search.setAlignment(Qt.AlignVCenter)
        self.search.setPlaceholderText('Search for element ...')
        self.search.setCompleter(self.completer)
        self.search.returnPressed.connect(self.Select)
        # Assign search and list
        self.layout().addWidget(self.search)
        self.context = QWidget()
        self.context.setLayout(QVBoxLayout())
        self.context.layout().setContentsMargins(0, 0, 0, 0)
        self.context.layout().setSpacing(10)
        self.context.setFixedHeight(120)
        # Element type
        self.type = QWidget()
        self.type.setLayout(QHBoxLayout())
        self.type.layout().setContentsMargins(0, 0, 0, 0)
        self.typeTitle = QLabel('Type')
        text = 'None' if not self.pvHasLinkedElement else self.pv.settings['linkedElement'].Type
        self.typeEdit = QLineEdit(text)
        self.typeEdit.setAlignment(Qt.AlignCenter)
        self.typeEdit.setFixedWidth(100)
        self.typeEdit.setEnabled(False)
        self.type.layout().addWidget(self.typeTitle, alignment = Qt.AlignLeft)
        self.type.layout().addWidget(self.typeEdit)
        self.type.layout().addItem(QSpacerItem(125, 0, QSizePolicy.Preferred, QSizePolicy.Preferred))
        # Element position
        self.position = QWidget()
        self.position.setLayout(QHBoxLayout())
        self.position.layout().setContentsMargins(0, 0, 0, 0)
        self.positionTitle = QLabel('Position (m)')
        text = 'None' if not self.pvHasLinkedElement else f'{self.pv.settings['linkedElement'].iloc[2]:.3f}'
        self.positionEdit = QLineEdit(text)
        self.positionEdit.setAlignment(Qt.AlignCenter)
        self.positionEdit.setFixedWidth(100)
        self.positionEdit.setEnabled(False)
        self.position.layout().addWidget(self.positionTitle, alignment = Qt.AlignLeft)
        self.position.layout().addWidget(self.positionEdit)
        self.position.layout().addItem(QSpacerItem(125, 0, QSizePolicy.Preferred, QSizePolicy.Preferred))
        # Element index
        self.index = QWidget()
        self.index.setLayout(QHBoxLayout())
        self.index.layout().setContentsMargins(0, 0, 0, 0)
        self.indexTitle = QLabel('Index')
        text = 'None' if not self.pvHasLinkedElement else f'{self.pv.settings['linkedElement'].Index}'
        self.indexEdit = QLineEdit(text)
        self.indexEdit.setAlignment(Qt.AlignCenter)
        self.indexEdit.setFixedWidth(100)
        self.indexEdit.setEnabled(False)
        self.index.layout().addWidget(self.indexTitle, alignment = Qt.AlignLeft)
        self.index.layout().addWidget(self.indexEdit)
        self.index.layout().addItem(QSpacerItem(125, 0, QSizePolicy.Preferred, QSizePolicy.Preferred))
        self.context.layout().addWidget(self.type)
        self.context.layout().addWidget(self.position)
        self.context.layout().addWidget(self.index)
        self.context.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.layout().addWidget(self.context)
        self.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))

        self.UpdateColors()

    def Select(self):
        self.search.clearFocus()
        split = self.search.text().split(' ')
        self.search.setText(split[0])
        self.linkedElement = shared.elements.iloc[int(split[2][1:-1])]
        self.typeEdit.setText(self.linkedElement.Type)
        self.positionEdit.setText(f'{self.linkedElement.iloc[2]:.3f}')
        self.indexEdit.setText(f'{self.linkedElement.Index}')
        self.pv.settings['linkedElement'] = self.linkedElement
        # linked element-specific logic
        if self.linkedElement.Type == 'Quadrupole':
            if 'alignment' in self.pv.settings:
                self.pv.settings.pop('alignment')
            self.pv.settings['components']['value']['name'] = 'Setpoint'
            self.pv.settings['components']['value']['units'] = 'm⁻²'
            self.pv.settings['components']['value']['value'] = shared.lattice[self.pv.settings['linkedElement'].Index].K
            self.pv.settings['components']['value']['default'] = shared.lattice[self.pv.settings['linkedElement'].Index].K
        elif self.linkedElement.Type == 'Corrector':
            self.pv.settings['alignment'] = 'Horizontal' if 'alignment' not in self.pv.settings else self.pv.settings['alignment']
            self.pv.settings['components']['value']['name'] = 'Kick'
            self.pv.settings['components']['value']['units'] = 'mrad'
            idx = 0 if self.pv.settings['alignment'] == 'Horizontal' else 1
            self.pv.settings['components']['value']['value'] = float(shared.lattice[self.pv.settings['linkedElement'].Index].KickAngle[idx])
            self.pv.settings['components']['value']['default'] = float(shared.lattice[self.pv.settings['linkedElement'].Index].KickAngle[idx])
        # Adjust slider range if necessary for the relevant types
        if self.linkedElement.Type in ['Corrector', 'Quadrupole']: # this list will grow over time
            if self.pv.settings['components']['value']['value'] < self.pv.settings['components']['value']['min']:
                self.pv.settings['components']['value']['min'] = self.pv.settings['components']['value']['value']
            elif self.pv.settings['components']['value']['value'] > self.pv.settings['components']['value']['max']:
                self.pv.settings['components']['value']['max'] = self.pv.settings['components']['value']['value']
        
        shared.inspector.Push(self.pv)

    def UpdateColors(self):
        if shared.lightModeOn:
            self.search.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.typeEdit.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.typeTitle.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e'))
            self.positionEdit.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.positionTitle.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e'))
            self.indexEdit.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.indexTitle.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e'))
        else:
            self.search.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
            self.typeEdit.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
            self.typeTitle.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
            self.positionEdit.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
            self.positionTitle.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
            self.indexEdit.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
            self.indexTitle.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))