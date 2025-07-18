from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt
from .. import shared
from .. import style

class ErrorsComponent(QWidget):
    '''Apply pitch, yaw and roll errors.'''
    def __init__(self, pv, component):
        super().__init__()
        self.pv = pv
        self.component = component
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(5, 0, 0, 5)
        self.layout().setSpacing(10)
        # Short description
        self.description = QLabel('Normal-distributed angle errors, or fixed offsets.')
        self.layout().addWidget(self.description)
        # Pitch
        self.pitchFixed = False
        self.pitchRow = QWidget()
        self.pitchRow.setFixedHeight(35)
        self.pitchRow.setLayout(QHBoxLayout())
        self.pitchRow.layout().setContentsMargins(0, 0, 0, 0)
        self.pitchLabel = QLabel('Pitch (Random), <span>&sigma;</span> :')
        self.pitchLabel.setStyleSheet(style.LabelStyle(fontColor = "#9A2F27", padding = 5))
        self.pitchLabel.setFixedWidth(135)
        self.pitchRow.layout().addWidget(self.pitchLabel, alignment = Qt.AlignLeft)
        # Pitch in mrad
        self.pitch = QLineEdit(f'{0:.1f}')
        self.pitch.returnPressed.connect(lambda: self.SetOffset('Pitch'))
        self.pitch.setAlignment(Qt.AlignCenter)
        self.pitch.setFixedWidth(65)
        self.pitchRow.layout().addWidget(self.pitch)
        # Add padding
        self.pitchRow.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        # Fix button
        self.pitchFix = QPushButton('Switch to Fixed')
        self.pitchFix.clicked.connect(lambda: self.SwitchMode('Pitch'))
        self.pitchFix.setFixedWidth(150)
        self.pitchRow.layout().addWidget(self.pitchFix)
        # Yaw
        self.yawFixed = False
        self.yawRow = QWidget()
        self.yawRow.setFixedHeight(35)
        self.yawRow.setLayout(QHBoxLayout())
        self.yawRow.layout().setContentsMargins(0, 0, 0, 0)
        self.yawLabel = QLabel('Yaw (Random), <span>&sigma;</span> :')
        self.yawLabel.setStyleSheet(style.LabelStyle(fontColor = "#279A38", padding = 5))
        self.yawLabel.setFixedWidth(135)
        self.yawRow.layout().addWidget(self.yawLabel, alignment = Qt.AlignLeft)
        # Yaw in mrad
        self.yaw = QLineEdit(f'{0:.1f}')
        self.yaw.returnPressed.connect(lambda: self.SetOffset('Yaw'))
        self.yaw.setAlignment(Qt.AlignCenter)
        self.yaw.setFixedWidth(65)
        self.yawRow.layout().addWidget(self.yaw)
        self.yawRow.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        # Fix button
        self.yawFix = QPushButton('Switch to Fixed')
        self.yawFix.clicked.connect(lambda: self.SwitchMode('Yaw'))
        self.yawFix.setFixedWidth(150)
        self.yawRow.layout().addWidget(self.yawFix)
        # Roll
        self.rollFixed = False
        self.rollRow = QWidget()
        self.rollRow.setFixedHeight(35)
        self.rollRow.setLayout(QHBoxLayout())
        self.rollRow.layout().setContentsMargins(0, 0, 0, 0)
        self.rollLabel = QLabel('Roll (Random), <span>&sigma;</span> :')
        self.rollLabel.setStyleSheet(style.LabelStyle(fontColor = "#27599A", padding = 5))
        self.rollLabel.setFixedWidth(135)
        self.rollRow.layout().addWidget(self.rollLabel, alignment = Qt.AlignLeft)
        # Roll in mrad
        self.roll = QLineEdit(f'{0:.1f}')
        self.roll.returnPressed.connect(lambda: self.SetOffset('Roll'))
        self.roll.setAlignment(Qt.AlignCenter)
        self.roll.setFixedWidth(65)
        self.rollRow.layout().addWidget(self.roll)
        self.rollRow.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        # Fix button
        self.rollFix = QPushButton('Switch to Fixed')
        self.rollFix.clicked.connect(lambda: self.SwitchMode('Roll'))
        self.rollFix.setFixedWidth(150)
        self.rollRow.layout().addWidget(self.rollFix)
        # Add rows to self
        self.layout().addWidget(self.pitchRow)
        self.layout().addWidget(self.yawRow)
        self.layout().addWidget(self.rollRow)
        # Update colors
        self.UpdateColors()

    def SwitchMode(self, nm):
        if nm == 'Pitch':
            self.pitchFixed = not self.pitchFixed
            if self.pitchFixed:
                self.pitchLabel.setText('Pitch (Fixed):')
                self.pitchFix.setText('Switch to Random')
            else:
                self.pitchLabel.setText('Pitch (Random), <span>&sigma;</span>:')
                self.pitchFix.setText('Switch to Fixed')
                if float(self.pitch.text()) < 0:
                    self.pitch.setText(f'{0:.1f}')
        elif nm == 'Yaw':
            self.yawFixed = not self.yawFixed
            if self.yawFixed:
                self.yawLabel.setText('Yaw (Fixed):')
                self.yawFix.setText('Switch to Random')
            else:
                self.yawLabel.setText('Yaw (Random), <span>&sigma;</span>:')
                self.yawFix.setText('Switch to Fixed')
                if float(self.yaw.text()) < 0:
                    self.yaw.setText(f'{0:.1f}')
        else:
            self.rollFixed = not self.rollFixed
            if self.rollFixed:
                self.rollLabel.setText('Roll (Fixed):')
                self.rollFix.setText('Switch to Random')
            else:
                self.rollLabel.setText('Roll (Random), <span>&sigma;</span>:')
                self.rollFix.setText('Switch to Fixed')
                if float(self.roll.text()) < 0:
                    self.roll.setText(f'{0:.1f}')

    def SetOffset(self, name):
        if name == 'Pitch':
            self.pitch.clearFocus()
            v = float(self.pitch.text())
            v = 0 if not self.pitchFixed and v < 0 else v
            self.pitch.setText(f'{v:.1f}')
        elif name == 'Yaw':
            self.yaw.clearFocus()
            v = float(self.yaw.text())
            v = 0 if not self.yawFixed and v < 0 else v
            self.yaw.setText(f'{v:.1f}')
        else:
            self.roll.clearFocus()
            v = float(self.roll.text())
            v = 0 if not self.rollFixed and v < 0 else v
            self.roll.setText(f'{v:.1f}')

    def UpdateColors(self):
        if shared.lightModeOn:
            self.description.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e', padding = 5))
            self.pitch.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.pitchFix.setStyleSheet(style.PushButtonStyle(color = '#D2C5A0', borderColor = '#A1946D', hoverColor = '#B5AB8D', fontColor = '#1e1e1e'))
            self.yaw.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.yawFix.setStyleSheet(style.PushButtonStyle(color = '#D2C5A0', borderColor = '#A1946D', hoverColor = '#B5AB8D', fontColor = '#1e1e1e'))
            self.roll.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.rollFix.setStyleSheet(style.PushButtonStyle(color = '#D2C5A0', borderColor = '#A1946D', hoverColor = '#B5AB8D', fontColor = '#1e1e1e'))
        else:
            self.description.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4', padding = 5))
            self.pitch.setStyleSheet(style.LineEditStyle(color = '#2d2d2d', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
            self.pitchFix.setStyleSheet(style.PushButtonStyle(color = '#363636', borderColor = '#1e1e1e', hoverColor = '#2d2d2d', fontColor = '#c4c4c4'))
            self.yaw.setStyleSheet(style.LineEditStyle(color = '#2d2d2d', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
            self.yawFix.setStyleSheet(style.PushButtonStyle(color = '#363636', borderColor = '#1e1e1e', hoverColor = '#2d2d2d', fontColor = '#c4c4c4'))
            self.roll.setStyleSheet(style.LineEditStyle(color = '#2d2d2d', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
            self.rollFix.setStyleSheet(style.PushButtonStyle(color = '#363636', borderColor = '#1e1e1e', hoverColor = '#2d2d2d', fontColor = '#c4c4c4'))