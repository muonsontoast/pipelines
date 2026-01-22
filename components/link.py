from PySide6.QtWidgets import QWidget, QLineEdit, QStyledItemDelegate, QCompleter, QComboBox, QLabel, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, QStringListModel
from .component import Component
from .. import shared
from .. import style
from ..lattice import latticeutils

# class LinkComponent(QWidget):
class LinkComponent(Component):
    def __init__(self, pv, component, expandable = None, **kwargs):
        super().__init__(pv, component, **kwargs)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 10, 0, 0)
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
            shared.names = [a + f' [{shared.elements.Type[b]}] (Index: {str(b)}) @ {shared.elements['s (m)'].iloc[b]:.2f} m' for a, b in zip(shared.elements.Name, shared.elements.Index)]
        # Completer
        self.completer = QCompleter()
        self.completer.setModel(QStringListModel(shared.names))
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setWrapAround(False)
        # Text search
        self.search = QLineEdit()
        self.search.setFixedSize(325, 30)
        self.search.setAlignment(Qt.AlignVCenter)
        self.search.setPlaceholderText('Search for element ...')
        if 'linkedElement' in self.pv.settings:
            self.search.setText(self.pv.settings['linkedElement'].Name)
        self.search.setCompleter(self.completer)
        self.search.returnPressed.connect(self.Select)
        # Assign search and list
        self.layout().addWidget(self.search)
        self.context = QWidget()
        self.context.setLayout(QVBoxLayout())
        self.context.layout().setContentsMargins(0, 0, 0, 0)
        self.context.layout().setSpacing(10)
        self.context.setFixedHeight(150)
        # Element type
        self.type = QWidget()
        self.type.setLayout(QHBoxLayout())
        self.type.layout().setContentsMargins(0, 0, 0, 0)
        self.type.layout().setSpacing(0)
        self.typeTitle = QLabel('Type')
        self.typeTitle.setFixedWidth(100)
        self.typeTitle.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.typeTitle.setAlignment(Qt.AlignLeft)
        text = 'None' if not self.pvHasLinkedElement else self.pv.settings['linkedElement'].Type
        self.typeEdit = QLineEdit(text)
        self.typeEdit.setAlignment(Qt.AlignCenter)
        self.typeEdit.setFixedWidth(100)
        self.typeEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.typeEdit.setEnabled(False)
        self.type.layout().addWidget(self.typeTitle, alignment = Qt.AlignLeft | Qt.AlignVCenter)
        self.type.layout().addWidget(self.typeEdit, alignment = Qt.AlignLeft)
        # Element position
        self.position = QWidget()
        self.position.setLayout(QHBoxLayout())
        self.position.layout().setContentsMargins(0, 0, 0, 0)
        self.position.layout().setSpacing(0)
        self.positionTitle = QLabel('Position (m)')
        self.positionTitle.setFixedWidth(100)
        self.positionTitle.setAlignment(Qt.AlignLeft)
        text = 'None' if not self.pvHasLinkedElement else f'{self.pv.settings['linkedElement'].iloc[2]:.3f}'
        self.positionEdit = QLineEdit(text)
        self.positionEdit.setAlignment(Qt.AlignCenter)
        self.positionEdit.setFixedWidth(100)
        self.positionEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.positionEdit.setEnabled(False)
        self.position.layout().addWidget(self.positionTitle, alignment = Qt.AlignLeft | Qt.AlignVCenter)
        self.position.layout().addWidget(self.positionEdit, alignment = Qt.AlignLeft)
        # Element index
        self.index = QWidget()
        self.index.setLayout(QHBoxLayout())
        self.index.layout().setContentsMargins(0, 0, 0, 0)
        self.index.layout().setSpacing(0)
        self.indexTitle = QLabel('Index')
        self.indexTitle.setFixedWidth(100)
        text = 'None' if not self.pvHasLinkedElement else f'{self.pv.settings['linkedElement'].Index}'
        self.indexEdit = QLineEdit(text)
        self.indexEdit.setAlignment(Qt.AlignCenter)
        self.indexEdit.setFixedWidth(100)
        self.indexEdit.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.indexEdit.setEnabled(False)
        self.index.layout().addWidget(self.indexTitle, alignment = Qt.AlignLeft | Qt.AlignVCenter)
        self.index.layout().addWidget(self.indexEdit, alignment = Qt.AlignLeft)
        self.context.layout().addWidget(self.type)
        self.context.layout().addWidget(self.position)
        self.context.layout().addWidget(self.index)
        # Data stream
        self.dtypesWidget = QWidget()
        self.dtypesWidget.setLayout(QHBoxLayout())
        self.dtypesWidget.layout().setContentsMargins(5, 0, 0, 0)
        self.dtypesWidget.layout().setSpacing(0)
        self.dtypesTitle = QLabel('Data Stream')
        self.dtypesTitle.setAlignment(Qt.AlignLeft)
        self.dtypesTitle.setFixedWidth(100)
        self.dtypesWidget.layout().addWidget(self.dtypesTitle, alignment = Qt.AlignLeft | Qt.AlignVCenter)
        # select text for the data edit
        self.dataComboBox = QComboBox()
        self.dataComboBox.setFixedWidth(100)
        self.dataComboBox.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.dataComboBox.view().parentWidget().setStyleSheet('color: transparent; background-color: transparent;')
        self.dataComboBox.addItems([f'    {dtype.upper()}' for dtype in self.pv.settings['dtypes']])
        idx = self.pv.settings['dtypes'].index(self.pv.settings['dtype'])
        self.dataComboBox.setCurrentIndex(idx)
        self.dtypesWidget.layout().addWidget(self.dataComboBox, alignment = Qt.AlignLeft)
        self.context.layout().addWidget(self.dtypesWidget)
        self.context.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.layout().addWidget(self.context)
        self.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding))

        self.defaultNames = ['PV', 'QUAD', 'VSTR', 'HSTR', 'BPM', 'AP', 'DRIFT', 'COLL']

        self.UpdateColors()

    def Select(self):
        self.search.clearFocus()
        try:
            idx = int(self.search.text().split('Index: ')[1].split(')')[0])
        except: # user has modified line edit text
            return
        self.linkedElement = shared.elements.iloc[idx]
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
        if self.pv.name.split()[0] in self.defaultNames or ('(Index: ' in self.pv.name and self.pv.name.split(' (Index: ')[0] in self.defaultNames):
            newName = self.linkedElement.Name + f' (Index: {self.linkedElement.Index})'
            self.pv.settings['name'] = newName
            self.pv.name = newName
            self.pv.title.setText(newName)
        print(self.linkedElement.Type)
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
            self.typeEdit.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 0))
            self.typeTitle.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
            self.positionEdit.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 0))
            self.positionTitle.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
            self.indexEdit.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 0))
            self.indexTitle.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
            self.dataComboBox.setStyleSheet(style.ComboStyle(color = '#1e1e1e', fontColor = '#c4c4c4', fontSize = 12, borderRadius = 6))