from PySide6.QtWidgets import (
    QWidget, QLineEdit, QSlider, QLabel, QPushButton,
    QGridLayout, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from . import shared
from . import style

class Value(QWidget):
    def __init__(self, pv, componentIdx, sliderSteps = 1000000, floatdp = 3):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.pv = pv
        self.componentIdx = componentIdx
        self.floatdp = int(floatdp)
        self.range = pv.settings['components'][componentIdx]['max'] - pv.settings['components'][componentIdx]['min']
        self.steps = sliderSteps
        # Slider row
        sliderRow = QWidget()
        sliderRow.setLayout(QHBoxLayout())
        sliderRow.setContentsMargins(0, 0, 0, 0)
        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setFixedWidth(150)
        self.slider.setRange(0, sliderSteps)
        self.slider.setValue(self.ToSliderValue(pv.settings['components'][componentIdx]['value']))
        self.slider.valueChanged.connect(self.UpdateSliderValue)
        sliderRow.layout().addWidget(self.slider, alignment = Qt.AlignLeft)
        sliderRow.layout().addItem(QSpacerItem(30, 0, QSizePolicy.Fixed, QSizePolicy.Fixed))
        # Value
        self.value = QLineEdit(f'{pv.settings['components'][componentIdx]['value']:.{self.floatdp}f}')
        self.value.setAlignment(Qt.AlignCenter)
        self.value.setFixedSize(75, 25)
        self.value.returnPressed.connect(self.SetSliderValue)
        sliderRow.layout().addWidget(self.value, alignment = Qt.AlignRight)
        sliderRow.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        # Reset
        self.resetButton = QPushButton('Reset')
        self.resetButton.setFixedWidth(65)
        self.resetButton.clicked.connect(self.Reset)
        # sliderRow.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        sliderRow.layout().addWidget(self.resetButton)
        # Context row
        contextRow = QWidget()
        contextRow.setLayout(QHBoxLayout())
        contextRow.setContentsMargins(0, 0, 0, 0)
        # Minimum
        self.minimumLabel = QLabel('Min')
        self.minimumLabel.setAlignment(Qt.AlignCenter)
        contextRow.layout().addWidget(self.minimumLabel, alignment = Qt.AlignLeft)
        self.minimum = QLineEdit(f'{pv.settings['components'][componentIdx]['min']:.{self.floatdp}f}')
        self.minimum.setAlignment(Qt.AlignCenter)
        self.minimum.setFixedSize(75, 25)
        self.minimum.returnPressed.connect(self.SetMinimum)
        contextRow.layout().addWidget(self.minimum)
        # Maximum
        self.maximumLabel = QLabel('Max')
        self.maximumLabel.setAlignment(Qt.AlignCenter)
        contextRow.layout().addWidget(self.maximumLabel, alignment = Qt.AlignLeft)
        self.maximum = QLineEdit(f'{pv.settings['components'][componentIdx]['max']:.{self.floatdp}f}')
        self.maximum.setAlignment(Qt.AlignCenter)
        self.maximum.setFixedSize(75, 25)
        self.maximum.returnPressed.connect(self.SetMaximum)
        contextRow.layout().addWidget(self.maximum)
        contextRow.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        # Default
        defaultRow = QWidget()
        defaultRow.setLayout(QHBoxLayout())
        defaultRow.setContentsMargins(0, 0, 0, 0)
        self.defaultLabel = QLabel('Default')
        self.defaultLabel.setAlignment(Qt.AlignCenter)
        defaultRow.layout().addWidget(self.defaultLabel, alignment = Qt.AlignLeft)
        self.default = QLineEdit(f'{pv.settings['components'][componentIdx]['default']:.{self.floatdp}f}')
        self.default.setAlignment(Qt.AlignCenter)
        self.default.setFixedSize(75, 25)
        self.default.returnPressed.connect(self.SetDefault)
        defaultRow.layout().addWidget(self.default)
        defaultRow.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))
        # Add rows
        self.layout().addWidget(sliderRow)
        self.layout().addWidget(contextRow)
        self.layout().addWidget(defaultRow)
        # Apply colors
        self.UpdateColors()

    def ToAbsolute(self, v):
        return self.pv.settings['components'][self.componentIdx]['min'] + v / self.steps * self.range
    
    def ToSliderValue(self, v):
        return (v - self.pv.settings['components'][self.componentIdx]['min']) / self.range * self.steps

    def UpdateSliderValue(self):
        v = self.ToAbsolute(self.slider.value())
        self.value.setText(f'{v:.{self.floatdp}f}')
        self.pv.settings['components'][self.componentIdx]['value'] = v

    def SetSliderValue(self):
        self.value.clearFocus()
        self.value.setText(f'{float(self.value.text()):.{self.floatdp}f}')
        self.pv.settings['components'][self.componentIdx]['value'] = float(self.value.text())
        self.UpdateSlider()

    def UpdateSlider(self):
        self.slider.setValue(self.ToSliderValue(float(self.value.text())))

    def Reset(self):
        self.slider.setValue(self.ToSliderValue(self.pv.settings['components'][self.componentIdx]['default']))

    def SetDefault(self):
        self.default.clearFocus()
        default = max(self.pv.settings['components'][self.componentIdx]['min'], min(self.pv.settings['components'][self.componentIdx]['max'], float(self.default.text())))
        self.default.setText(f'{default:.{self.floatdp}f}')
        self.pv.settings['components'][self.componentIdx]['default'] = default

    def SetMinimum(self):
        self.minimum.clearFocus()
        v = float(self.minimum.text())
        self.pv.settings['components'][self.componentIdx]['min'] = v
        self.pv.settings['components'][self.componentIdx]['default'] = max(v, self.pv.settings['components'][self.componentIdx]['default'])
        self.default.setText(f'{self.pv.settings['components'][self.componentIdx]['default']:.{self.floatdp}f}')
        self.range = self.pv.settings['components'][self.componentIdx]['max'] - v
        self.default.setText(f'{self.pv.settings['components'][self.componentIdx]['default']:.{self.floatdp}f}')
        self.minimum.setText(f'{v:.{self.floatdp}f}')
        newSliderValue = max(float(self.value.text()), v)
        self.slider.setValue(self.ToSliderValue(newSliderValue))
        self.value.setText(f'{newSliderValue:.{self.floatdp}f}')
        self.pv.settings['components'][self.componentIdx]['value'] = newSliderValue
    
    def SetMaximum(self):
        self.maximum.clearFocus()
        v = float(self.maximum.text())
        self.pv.settings['components'][self.componentIdx]['max'] = v
        self.pv.settings['components'][self.componentIdx]['default'] = min(v, self.pv.settings['components'][self.componentIdx]['default'])
        self.default.setText(f'{self.pv.settings['components'][self.componentIdx]['default']:.{self.floatdp}f}')
        self.range = v - self.pv.settings['components'][self.componentIdx]['min']
        self.maximum.setText(f'{v:.{self.floatdp}f}')
        newSliderValue = min(float(self.value.text()), v)
        self.slider.setValue(self.ToSliderValue(newSliderValue))
        self.value.setText(f'{newSliderValue:.{self.floatdp}f}')
        self.pv.settings['components'][self.componentIdx]['value'] = newSliderValue

    def UpdateColors(self):
        if shared.lightModeOn:
            self.slider.setStyleSheet(style.SliderStyle(backgroundColor = "#D2C5A0", fillColor = "#B23838", handleColor = "#2A2A2A"))
            self.minimum.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.maximum.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.value.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.default.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = 5, paddingBottom = 5))
            self.minimumLabel.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e'))
            self.maximumLabel.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e'))
            self.defaultLabel.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e'))
            self.resetButton.setStyleSheet(style.PushButtonStyle(color = '#D2C5A0', borderColor = '#A1946D', hoverColor = '#B5AB8D', fontColor = '#1e1e1e', padding = 4))
            return
        self.slider.setStyleSheet(style.SliderStyle(backgroundColor = "#2d2d2d", fillColor = "#3FA466", handleColor = "#5d5d5d"))
        self.minimum.setStyleSheet(style.LineEditStyle(color = '#2d2d2d', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
        self.maximum.setStyleSheet(style.LineEditStyle(color = '#2d2d2d', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
        self.value.setStyleSheet(style.LineEditStyle(color = '#2d2d2d', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
        self.default.setStyleSheet(style.LineEditStyle(color = '#2d2d2d', fontColor = '#c4c4c4', paddingLeft = 5, paddingBottom = 5))
        self.minimumLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
        self.maximumLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
        self.defaultLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
        self.resetButton.setStyleSheet(style.PushButtonStyle(color = '#363636', borderColor = '#1e1e1e', hoverColor = '#2d2d2d', fontColor = '#c4c4c4', padding = 4))