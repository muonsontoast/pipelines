from PySide6.QtWidgets import (
    QWidget, QLineEdit, QSlider, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
import numpy as np
from .. import shared
from .. import style

class SliderBar(QSlider):
    def __init__(self, orientation, parent):
        super().__init__(orientation)
        self.parent = parent

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

class SliderComponent(QWidget):
    def __init__(self, pv, component, sliderSteps = 1000000, floatdp = 3, **kwargs):
        '''Leave `sliderSteps` at 1e6 for smooth sliding, or restrict to a low number for discrete applications.\n
        `floatdp` is the decimal precision of the line edit elements.\n
        `hideRange` allows you to supress the min and max widgets.\n
        `sliderOffset` (int) adds a horizontal offset to the slider row.\n
        `sliderRowSpacing` (int) controls width of SpacerItem between the slider and slider value.\n
        `paddingLeft` and `paddingBottom` (int) are padding for text inside line edit elements.'''
        super().__init__()
        self.eps = 9e-4
        self.hideRange = kwargs.get('hideRange', False)
        self.sliderOffset = kwargs.get('sliderOffset', 0)
        self.paddingLeft = kwargs.get('paddingLeft', 5)
        self.paddingBottom = kwargs.get('paddingBottom', 5)
        self.sliderOffset = kwargs.get('sliderOffset', 5)
        self.sliderRowSpacing = kwargs.get('sliderRowSpacing', 20)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(self.sliderOffset, 0, 0, 15)
        self.layout().setSpacing(10)
        self.pv = pv
        self.component = component
        self.floatdp = int(floatdp)
        self.range = pv.settings['components'][component]['max'] - pv.settings['components'][component]['min']
        self.steps = sliderSteps
        # Slider row
        self.sliderRow = QWidget()
        self.sliderRow.setLayout(QHBoxLayout())
        self.sliderRow.layout().setContentsMargins(self.sliderOffset, 0, 0, 0)
        self.sliderRow.layout().setSpacing(0)
        # Slider
        self.slider = SliderBar(Qt.Horizontal, self)
        self.slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.slider.setRange(0, sliderSteps)
        self.slider.setValue(self.ToSliderValue(pv.settings['components'][component]['value']))
        self.slider.valueChanged.connect(self.UpdateSliderValue)
        self.slider.valueChanged.connect(self.UpdatePVSetValueCheck)
        self.sliderRow.layout().addWidget(self.slider)
        self.sliderRow.layout().addItem(QSpacerItem(self.sliderRowSpacing, 0, QSizePolicy.Fixed, QSizePolicy.Preferred))
        # Value
        v = f'{pv.settings['components'][component]['value']:.{self.floatdp}f}' if pv.settings['components'][component]['value'] > self.eps else '0.000'
        self.value = QLineEdit(v)
        self.value.setAlignment(Qt.AlignCenter)
        self.value.setFixedSize(75, 25)
        self.value.returnPressed.connect(self.SetSliderValue)
        self.sliderRow.layout().addWidget(self.value, alignment = Qt.AlignRight)
        self.sliderRow.layout().addItem(QSpacerItem(self.sliderRowSpacing, 0, QSizePolicy.Fixed, QSizePolicy.Preferred))
        # Reset
        self.resetButton = QPushButton('Reset')
        self.resetButton.setFixedWidth(65)
        self.resetButton.clicked.connect(self.Reset)
        self.sliderRow.layout().addWidget(self.resetButton)
        if not self.hideRange:
            # Minimum
            self.minimumRow = QWidget()
            self.minimumRow.setLayout(QHBoxLayout())
            self.minimumRow.layout().setContentsMargins(0, 0, 0, 0)
            self.minimumLabel = QLabel('Minimum')
            self.minimumLabel.setAlignment(Qt.AlignCenter)
            self.minimum = QLineEdit(f'{pv.settings['components'][component]['min']:.{self.floatdp}f}')
            self.minimum.setAlignment(Qt.AlignCenter)
            self.minimum.setFixedSize(75, 25)
            self.minimum.returnPressed.connect(self.SetMinimum)
            self.minimumRow.layout().addWidget(self.minimumLabel, alignment = Qt.AlignLeft)
            self.minimumRow.layout().addWidget(self.minimum, alignment = Qt.AlignRight)
            self.minimumRow.layout().addItem(QSpacerItem(200, 0, QSizePolicy.Preferred, QSizePolicy.Preferred))
            # Maximum
            self.maximumRow = QWidget()
            self.maximumRow.setLayout(QHBoxLayout())
            self.maximumRow.layout().setContentsMargins(0, 0, 0, 0)
            self.maximumLabel = QLabel('Maximum')
            self.maximumLabel.setAlignment(Qt.AlignCenter)
            self.maximum = QLineEdit(f'{pv.settings['components'][component]['max']:.{self.floatdp}f}')
            self.maximum.setAlignment(Qt.AlignCenter)
            self.maximum.setFixedSize(75, 25)
            self.maximum.returnPressed.connect(self.SetMaximum)
            self.maximumRow.layout().addWidget(self.maximumLabel, alignment = Qt.AlignLeft)
            self.maximumRow.layout().addWidget(self.maximum, alignment = Qt.AlignRight)
            self.maximumRow.layout().addItem(QSpacerItem(200, 0, QSizePolicy.Preferred, QSizePolicy.Preferred))
            # Default
            self.defaultRow = QWidget()
            self.defaultRow.setLayout(QHBoxLayout())
            self.defaultRow.layout().setContentsMargins(0, 0, 0, 0)
            self.defaultLabel = QLabel('Default')
            self.defaultLabel.setAlignment(Qt.AlignCenter)
            self.defaultRow.layout().addWidget(self.defaultLabel, alignment = Qt.AlignLeft)
            self.default = QLineEdit(f'{pv.settings['components'][component]['default']:.{self.floatdp}f}')
            self.default.setAlignment(Qt.AlignCenter)
            self.default.setFixedSize(75, 25)
            self.default.returnPressed.connect(self.SetDefault)
            self.defaultRow.layout().addWidget(self.default, alignment = Qt.AlignRight)
            self.defaultRow.layout().addItem(QSpacerItem(200, 0, QSizePolicy.Preferred, QSizePolicy.Preferred))
        # Add rows
        self.layout().addWidget(self.sliderRow)
        if not self.hideRange:
            self.layout().addWidget(self.minimumRow)
            self.layout().addWidget(self.maximumRow)
            self.layout().addWidget(self.defaultRow)
        # Apply colors
        self.UpdateColors()

    def UpdatePVSetValueCheck(self):
        # If this block has a SET value, it will automatically update it as the slider value changes
        if self.pv is not None:
            if hasattr(self.pv, 'set'):
                # v = self.value.text() if abs(float(self.value.text()) > self.eps else '0.000'
                self.pv.set.setText(v)

    def ToAbsolute(self, v):
        self.range = 1 if self.range == 0 else self.range
        return self.pv.settings['components'][self.component]['min'] + v / self.steps * self.range
    
    def ToSliderValue(self, v):
        self.range = 1 if self.range == 0 else self.range
        return (v - self.pv.settings['components'][self.component]['min']) / self.range * self.steps

    def UpdateSliderValue(self):
        v = self.ToAbsolute(self.slider.value())
        v = v if np.abs(v) > self.eps else 0
        self.value.setText(f'{v:.{self.floatdp}f}')
        if 'valueType' not in self.pv.settings['components'][self.component].keys():
            self.pv.settings['components'][self.component]['valueType'] = float
        self.pv.settings['components'][self.component]['value'] = self.pv.settings['components'][self.component]['valueType'](v)
        if 'linkedElement' in self.pv.settings:
            print('About to update it\'s linked element')
            self.pv.UpdateLinkedElement(self.slider, self.ToAbsolute)
        else:
            if self.pv.type in self.pv.pvBlockTypes:
                self.pv.data[0] = v

    def SetSliderValue(self):
        self.value.clearFocus()
        v = self.value.text() if float(self.value.text()) > self.eps else '0.000'
        self.value.setText(v)
        if 'valueType' not in self.pv.settings['components'][self.component].keys():
            self.pv.settings['components'][self.component]['valueType'] = float
        self.pv.settings['components'][self.component]['value'] = self.pv.settings['components'][self.component]['valueType'](self.value.text())
        if self.hideRange: # blinking cursor error in proxy widgets, so redraw the line edit.
            value = QLineEdit(f'{self.pv.settings['components'][self.component]['value']:.{self.floatdp}f}')
            value.setAlignment(Qt.AlignCenter)
            value.setFixedSize(75, 25)
            value.returnPressed.connect(self.SetSliderValue)
            self.sliderRow.layout().replaceWidget(self.value, value)
            self.value.setParent(None)
            self.value.deleteLater()
            shared.app.processEvents()
            self.value = value
            self.UpdateColors()
        self.UpdateSlider()

    def UpdateSlider(self):
        newValue = float(self.value.text())
        self.slider.setValue(self.ToSliderValue(newValue))
        if 'linkedElement' in self.pv.settings:
            print('About to update it\'s linked element')
            self.pv.UpdateLinkedElement(self.slider, self.ToAbsolute)
        else:
            self.pv.data[0] = self.ToAbsolute(self.slider.value())

    def Reset(self):
        self.slider.setValue(self.ToSliderValue(self.pv.settings['components'][self.component]['default']))
        if 'linkedElement' in self.pv.settings:
            print('About to update it\'s linked element')
            self.pv.UpdateLinkedElement(self.slider, self.ToAbsolute)
        else:
            self.pv.data[0] = self.ToAbsolute(self.slider.value())
        self.UpdatePVSetValueCheck()

    def SetDefault(self, override = False):
        if not override:
            self.default.clearFocus()
            default = max(self.pv.settings['components'][self.component]['min'], min(self.pv.settings['components'][self.component]['max'], float(self.default.text())))
            v = default if default > self.eps else 0
            self.default.setText(f'{v:.{self.floatdp}f}')
        else:
            default = max(self.pv.settings['components'][self.component]['min'], min(self.pv.settings['components'][self.component]['max'], self.pv.settings['components'][self.component]['default']))
        
        self.pv.settings['components'][self.component]['default'] = default
        
        if not self.hideRange: # blinking cursor error in proxy widgets, so redraw the line edit.
            default = QLineEdit(f'{self.pv.settings['components'][self.component]['default']:.{self.floatdp}f}')
            default.setAlignment(Qt.AlignCenter)
            default.setFixedSize(75, 25)
            default.returnPressed.connect(self.SetDefault)
            self.defaultRow.layout().replaceWidget(self.default, default)
            self.default.setParent(None)
            self.default.deleteLater()
            shared.app.processEvents()
            self.default = default
            self.UpdateColors()
        self.UpdatePVSetValueCheck()

    def SetMinimum(self, override = False):
        '''`override` is a bool. Component should be updated before calling this override. '''
        if not override:
            self.minimum.clearFocus()
            v = float(self.minimum.text())
            if v >= self.pv.settings['components'][self.component]['max']:
                return
            self.pv.settings['components'][self.component]['min'] = v
            self.pv.settings['components'][self.component]['default'] = max(v, self.pv.settings['components'][self.component]['default'])
            formattedDefault = self.pv.settings['components'][self.component]['default'] if self.pv.settings['components'][self.component]['default'] > self.eps else 0
            self.default.setText(f'{formattedDefault:.{self.floatdp}f}')
            self.range = self.pv.settings['components'][self.component]['max'] - v
            # self.default.setText(f'{self.pv.settings['components'][self.component]['default']:.{self.floatdp}f}')
            formattedMin = v if v > self.eps else 0
            self.minimum.setText(f'{formattedMin:.{self.floatdp}f}')
            newSliderValue = max(float(self.value.text()), v)
            formattedValue = newSliderValue if newSliderValue > self.eps else 0
            self.value.setText(f'{formattedValue:.{self.floatdp}f}')
        else:
            self.range = 1
            self.slider.setRange(0, self.pv.settings['components'][self.component]['max'] - self.pv.settings['components'][self.component]['min'] - 1)
            newSliderValue = max(self.pv.settings['components'][self.component]['value'], self.pv.settings['components'][self.component]['min'])

        self.pv.settings['components'][self.component]['value'] = newSliderValue
        self.slider.setValue(self.ToSliderValue(newSliderValue)) # assign the value of the slider

        if not self.hideRange: # blinking cursor error in proxy widgets, so redraw the line edit.
            minimum = QLineEdit(f'{self.pv.settings['components'][self.component]['min']:.{self.floatdp}f}')
            minimum.setAlignment(Qt.AlignCenter)
            minimum.setFixedSize(75, 25)
            minimum.returnPressed.connect(self.SetMinimum)
            self.minimumRow.layout().replaceWidget(self.minimum, minimum)
            self.minimum.setParent(None)
            self.minimum.deleteLater()
            shared.app.processEvents()
            self.minimum = minimum
            self.UpdateColors()
        self.UpdatePVSetValueCheck()
    
    def SetMaximum(self, override = False):
        '''`override` is a bool. Component should be updated before calling this override. '''
        print('setting maximum ...')
        if not override:
            self.maximum.clearFocus()
            v = float(self.maximum.text())
            if v <= self.pv.settings['components'][self.component]['min']:
                return
            self.pv.settings['components'][self.component]['max'] = v
            self.pv.settings['components'][self.component]['default'] = min(v, self.pv.settings['components'][self.component]['default'])
            self.default.setText(f'{self.pv.settings['components'][self.component]['default']:.{self.floatdp}f}')
            self.range = v - self.pv.settings['components'][self.component]['min']
            self.maximum.setText(f'{v:.{self.floatdp}f}')
            newSliderValue = min(float(self.value.text()), v)
            self.value.setText(f'{newSliderValue:.{self.floatdp}f}')
        else:
            self.range = 1
            self.slider.setRange(0, self.pv.settings['components'][self.component]['max'] - 1)
            newSliderValue = min(self.pv.settings['components'][self.component]['value'], self.pv.settings['components'][self.component]['max'])
        
        self.pv.settings['components'][self.component]['value'] = newSliderValue
        self.slider.setValue(self.ToSliderValue(newSliderValue))
        
        if not self.hideRange: # blinking cursor error in proxy widgets, so redraw the line edit.
            maximum = QLineEdit(f'{self.pv.settings['components'][self.component]['max']:.{self.floatdp}f}')
            maximum.setAlignment(Qt.AlignCenter)
            maximum.setFixedSize(75, 25)
            maximum.returnPressed.connect(self.SetMaximum)
            self.maximumRow.layout().replaceWidget(self.maximum, maximum)
            self.maximum.setParent(None)
            self.maximum.deleteLater()
            shared.app.processEvents()
            self.maximum = maximum
            self.UpdateColors()
        self.UpdatePVSetValueCheck()

    def UpdateColors(self, **kwargs):
        '''Override `fillColorLight` and `fillColorDark` with a #ABCDEF color string.'''
        fillColorDark = kwargs.get('fillColorDark', "#4E4E4E")
        fillColorLight = kwargs.get('fillColorLight', "#AFAFAF")
        if shared.lightModeOn:
            self.slider.setStyleSheet(style.SliderStyle(backgroundColor = "#D2C5A0", fillColor = fillColorLight, handleColor = "#2E2E2E"))
            self.value.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))
            if not self.hideRange:
                self.minimum.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))
                self.maximum.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))
                self.minimumLabel.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e'))
                self.maximumLabel.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e'))
                self.default.setStyleSheet(style.LineEditStyle(color = '#D2C5A0', fontColor = '#1e1e1e', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))
                self.defaultLabel.setStyleSheet(style.LabelStyle(fontColor = '#1e1e1e'))
            self.resetButton.setStyleSheet(style.PushButtonStyle(color = '#D2C5A0', borderColor = '#A1946D', hoverColor = '#B5AB8D', fontColor = '#1e1e1e', padding = 4))
            return
        self.slider.setStyleSheet(style.SliderStyle(backgroundColor = "#222222", fillColor = fillColorDark, handleColor = "#858585"))
        self.value.setStyleSheet(style.LineEditStyle(color = '#222222', bold = True, fontColor = '#c4c4c4', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))
        if not self.hideRange:
            self.minimum.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))
            self.maximum.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))
            self.minimumLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
            self.maximumLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
            self.default.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = self.paddingLeft, paddingBottom = self.paddingBottom))
            self.defaultLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
        self.resetButton.setStyleSheet(style.PushButtonStyle(color = '#2e2e2e', hoverColor = '#3e3e3e', fontColor = '#c4c4c4', padding = 5))