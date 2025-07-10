from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt

class PVLimits(QWidget):
    def __init__(self, window, min = 0, max = 100):
        super().__init__()
        self.parent = window
        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(40)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(f'''
        QLineEdit {{
        color: {self.parent.fontColor};
        background-color: {self.parent.buttonColor};
        font-size: {self.parent.fontSize};
        font-family: {self.parent.fontFamily};
        }}
        QPushButton {{
        color: {self.parent.fontColor};
        background-color: {self.parent.buttonColor};
        font-size: {self.parent.fontSize};
        font-family: {self.parent.fontFamily};
        }}
        ''')
        self.minimumHousing = QWidget()
        self.minimumHousing.setLayout(QHBoxLayout())
        self.minimumHousing.layout().setSpacing(5)
        self.minimumHousing.layout().setContentsMargins(0, 0, 0, 0)
        self.minimumHousing.setFixedWidth(130)
        # self.minimumHousing.setFixedHeight(45)
        self.maximumHousing = QWidget()
        self.maximumHousing.setLayout(QHBoxLayout())
        self.maximumHousing.layout().setSpacing(5)
        self.maximumHousing.layout().setContentsMargins(0, 0, 0, 0)
        self.maximumHousing.setFixedWidth(130)
        # self.maximumHousing.setFixedHeight(45)
        self.minimum = QLineEdit(self)
        # self.minimum.setFixedWidth(50)
        self.minimum.setAlignment(Qt.AlignCenter)
        self.minimum.setText(f'{min:.3f}')
        self.maximum = QLineEdit(self)
        # self.maximum.setFixedWidth(50)
        self.maximum.setAlignment(Qt.AlignCenter)
        self.maximum.setText(f'{max:.3f}')
        self.minimumHousing.layout().addWidget(QLabel('Minimum'), stretch = 1)
        self.minimumHousing.layout().addWidget(self.minimum, stretch = 2)
        self.maximumHousing.layout().addWidget(QLabel('Maximum'), stretch = 1)
        self.maximumHousing.layout().addWidget(self.maximum, stretch = 2)
        self.layout().addWidget(self.minimumHousing)
        self.layout().addWidget(self.maximumHousing)
        self.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        # Connect functions
        self.minimum.returnPressed.connect(self.SetMinimum)
        self.maximum.returnPressed.connect(self.SetMaximum)

    def SetMinimum(self):
        self.minimum.clearFocus()
        self.minimum.setText(f'{float(self.minimum.text()):.3f}')

    def SetMaximum(self):
        self.maximum.clearFocus()
        self.maximum.setText(f'{float(self.maximum.text()):.3f}')