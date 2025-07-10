from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt

class PVDefault(QFrame):
    def __init__(self, window, value = 0):
        super().__init__()
        self.parent = window
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.default = QLineEdit(f'{value:.3f}')
        self.default.setFixedSize(65, 20)
        self.default.setAlignment(Qt.AlignCenter)
        self.default.setStyleSheet(f'''
        QLineEdit {{
        color: {self.parent.fontColor};
        background-color: {self.parent.buttonColor};
        font-size: {self.parent.fontSize};
        font-family: {self.parent.fontFamily};
        }}
        ''')
        self.layout().addWidget(self.default)
        # Spacing
        self.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        # Connect functions
        self.default.returnPressed.connect(self.SetValue)

    def SetValue(self):
        self.default.clearFocus()
        self.default.setText(f'{float(self.default.text()):.3f}')