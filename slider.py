from PySide6.QtWidgets import QFrame, QSlider, QLineEdit, QPushButton, QSpacerItem, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from .font import SetFontToBold

class PVSlider(QFrame):
    def __init__(self, window, steps = 1000000, **kwargs):
        '''`color` is the color of the slider region to the left of the handle.'''
        color = kwargs.get('color', '#733DE6')
        super().__init__()
        self.parent = window
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(10)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet(f'''
        QLineEdit {{
        color: {self.parent.fontColor};
        background-color: {self.parent.buttonColor};
        }}
        QPushButton {{
        color: {self.parent.fontColor};
        background-color: {self.parent.buttonColor};
        }}
        ''')
        self.steps = steps
        # Add a slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setFixedWidth(150)
        self.slider.setFixedHeight(24)
        self.slider.setMinimum(0)
        self.slider.setMaximum(steps)
        self.slider.setStyleSheet(f'''
        QSlider::groove:horizontal {{
            border: .5px solid #2E2E2E;
            height: 4px;
            background: #2E2E2E;
        }}
        QSlider::handle:horizontal {{
            background: #5B4981;
            width: 12px;
            height: 12px;
            margin: -5px 0;  /* lets it bulge above and below */
            border-radius: 2px;
            border: 1px solid #858585;
        }}
        QSlider::sub-page:horizontal {{
            background: {color};                    
        }}''')
        # Value line edit
        self.sliderValue = QLineEdit(f'{0:.3f}')
        self.sliderValue.setAlignment(Qt.AlignCenter)
        self.sliderValue.setFixedWidth(65)
        self.range = [0, 100]
        self.default = 0
        # Reset button
        self.sliderReset = QPushButton('Reset')
        self.sliderReset.setFixedWidth(65)
        self.layout().addWidget(self.slider)
        self.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self.layout().addWidget(self.sliderValue, alignment = Qt.AlignRight)
        self.layout().addWidget(self.sliderReset, alignment = Qt.AlignRight)
        # connect functions
        self.slider.valueChanged.connect(self.UpdateSliderValue)
        self.sliderReset.clicked.connect(self.ResetSliderValue)
        self.sliderReset.pressed.connect(self.PressReset)
        self.sliderReset.pressed.connect(self.ReleaseReset)

    def UpdateSliderValue(self):
        self.sliderValue.setText(f'{self.ToAbsoluteValue(self.slider.value()):.3f}')

    def ResetSliderValue(self):
        self.slider.setValue(self.ToSliderValue(self.default))

    def PressReset(self):
        self.sliderReset.setStyleSheet(f'''
        QPushButton {{
        background-color: {self.parent.buttonPressedColor};
        color: {self.parent.fontColor};
        font-size: {self.parent.fontSize};
        font-family: {self.parent.fontFamily};
        font-weight: bold;
        padding: 5px;
        border: 2px solid {self.parent.buttonBorderColor};
        border-radius: 3px;
        }}
        ''')

    def ReleaseReset(self):
        self.sliderReset.setStyleSheet(f'''
        QPushButton {{
        background-color: {self.parent.buttonColor};
        color: {self.parent.fontColor};
        font-size: {self.parent.fontSize};
        font-family: {self.parent.fontFamily};
        font-weight: bold;
        padding: 5px;
        border: 2px solid {self.buttonBorderColor};
        border-radius: 3px;
        }}
        ''')

    def ToSliderValue(self, v):
        return (v - self.range[0]) / (self.range[1] - self.range[0]) * self.steps
    
    def ToAbsoluteValue(self, v):
        return (v / self.steps) * (self.range[1] - self.range[0]) + self.range[0]