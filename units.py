from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt

class PVUnits(QFrame):
    def __init__(self, window, units = ''):
        super().__init__()
        self.parent = window
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.units = QLineEdit(units)
        self.units.setFixedSize(65, 20)
        self.units.setAlignment(Qt.AlignCenter)
        self.units.setStyleSheet(f'''
        QLineEdit {{
        color: {self.parent.fontColor};
        background-color: {self.parent.buttonColor};
        font-size: {self.parent.fontSize};
        font-family: {self.parent.fontFamily};
        }}
        ''')
        self.layout().addWidget(self.units)
        # Add padding
        self.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        # Connect functions
        self.units.returnPressed.connect(self.SetUnits)

    def SetUnits(self):
        self.units.clearFocus()