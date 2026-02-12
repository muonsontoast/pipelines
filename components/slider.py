from PySide6.QtWidgets import (
    QWidget, QLineEdit, QSlider, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QCheckBox,
)
from PySide6.QtCore import Qt
import numpy as np
from .component import Component
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

# class SliderComponent(QWidget):
class SliderComponent(Component):
    def __init__(self, pv, component, sliderSteps = 1000000, floatdp = 3, expandable = None, **kwargs):
        '''Leave `sliderSteps` at 1e6 for smooth sliding, or restrict to a low number for discrete applications.\n
        `floatdp` is the decimal precision of the line edit elements.\n
        `hideRange` allows you to supress the min and max widgets.\n
        `sliderOffset` (int) adds a horizontal offset to the slider row.\n
        `sliderRowSpacing` (int) controls width of SpacerItem between the slider and slider value.\n
        `paddingLeft` and `paddingBottom` (int) are padding for text inside line edit elements.'''
        super().__init__(pv, component, expandable, **kwargs)
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
        self.slider.valueChanged.connect(self.UpdateSliderValue)
        self.slider.valueChanged.connect(self.UpdatePVSetValueCheck)
        self.sliderRow.layout().addWidget(self.slider)
        self.sliderRow.layout().addItem(QSpacerItem(self.sliderRowSpacing, 0, QSizePolicy.Fixed, QSizePolicy.Preferred))
        # Value
        self.value = QLineEdit()
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
            self.minimumRow.layout().setSpacing(0)
            self.minimumLabel = QLabel('Minimum')
            self.minimumLabel.setFixedWidth(100)
            self.minimumLabel.setAlignment(Qt.AlignLeft)
            self.minimum = QLineEdit()
            self.minimum.setAlignment(Qt.AlignCenter)
            self.minimum.setFixedSize(75, 25)
            self.minimum.returnPressed.connect(self.SetMinimum)
            self.minimumRow.layout().addWidget(self.minimumLabel, alignment = Qt.AlignLeft)
            self.minimumRow.layout().addWidget(self.minimum, alignment = Qt.AlignLeft)
            # Maximum
            self.maximumRow = QWidget()
            self.maximumRow.setLayout(QHBoxLayout())
            self.maximumRow.layout().setContentsMargins(0, 0, 0, 0)
            self.maximumRow.layout().setSpacing(0)
            self.maximumLabel = QLabel('Maximum')
            self.maximumLabel.setFixedWidth(100)
            self.maximumLabel.setAlignment(Qt.AlignLeft)
            self.maximum = QLineEdit()
            self.maximum.setAlignment(Qt.AlignCenter)
            self.maximum.setFixedSize(75, 25)
            self.maximum.returnPressed.connect(self.SetMaximum)
            self.maximumRow.layout().addWidget(self.maximumLabel, alignment = Qt.AlignLeft)
            self.maximumRow.layout().addWidget(self.maximum, alignment = Qt.AlignLeft)
            # Default
            self.defaultRow = QWidget()
            self.defaultRow.setLayout(QHBoxLayout())
            self.defaultRow.layout().setContentsMargins(0, 0, 0, 0)
            self.defaultRow.layout().setSpacing(0)
            self.defaultLabel = QLabel('Default')
            self.defaultLabel.setFixedWidth(100)
            self.defaultLabel.setAlignment(Qt.AlignLeft)
            self.default = QLineEdit()
            self.default.setAlignment(Qt.AlignCenter)
            self.default.setFixedSize(75, 25)
            self.default.returnPressed.connect(self.SetDefault)
            self.defaultRow.layout().addWidget(self.defaultLabel, alignment = Qt.AlignLeft)
            self.defaultRow.layout().addWidget(self.default, alignment = Qt.AlignLeft)
            # make read-only if there is a PV match
            if hasattr(self.pv, 'PVMatch') and self.pv.PVMatch:
                self.minimum.setReadOnly(True)
                self.maximum.setReadOnly(True)
                self.default.setReadOnly(True)
        # Advanced
        self.advanced = QWidget()
        self.advanced.setFixedSize(225, 35)
        self.advanced.setLayout(QHBoxLayout())
        self.advanced.layout().setContentsMargins(0, 0, 0, 0)
        self.advanced.layout().setSpacing(10)
        self.advancedLabel = QLabel('ADVANCED')
        self.advanced.layout().addWidget(self.advancedLabel)
        # Magnitude only
        self.magnitudeRow = QWidget()
        self.magnitudeRow.setLayout(QHBoxLayout())
        self.magnitudeRow.layout().setContentsMargins(0, 0, 0, 0)
        self.magnitudeRow.layout().setSpacing(5)
        self.magnitudeLabel = QLabel('Magnitude Only?')
        self.magnitudeLabel.setFixedSize(125, 35)
        self.magnitudeState = QLineEdit('Yes' if self.pv.settings['magnitudeOnly'] else 'No')
        self.magnitudeState.setFixedSize(50, 25)
        self.magnitudeState.setAlignment(Qt.AlignCenter)
        self.magnitudeState.setEnabled(False)
        self.magnitudeSwitch = QPushButton('Switch')
        self.magnitudeSwitch.setFixedWidth(65)
        self.magnitudeSwitch.pressed.connect(self.ToggleMagnitudeState)
        self.magnitudeRow.layout().addWidget(self.magnitudeLabel, alignment = Qt.AlignLeft | Qt.AlignVCenter)
        self.magnitudeRow.layout().addWidget(self.magnitudeState, alignment = Qt.AlignLeft | Qt.AlignVCenter)
        self.magnitudeRow.layout().addWidget(self.magnitudeSwitch)

        # Conditional multiple block logic
        self.slider.blockSignals(True)
        if not shared.activeEditor.area.multipleBlocksSelected:
            self.slider.setValue(self.ToSliderValue(pv.settings['components'][component]['value']))
            v = f'{pv.settings['components'][component]['value']:.{self.floatdp}f}' if np.abs(pv.settings['components'][component]['value']) > self.eps else '0.000'
            self.value.setText(v)
            self.minimum.setText(f'{pv.settings['components'][component]['min']:.{self.floatdp}f}')
            self.maximum.setText(f'{pv.settings['components'][component]['max']:.{self.floatdp}f}')
            self.default.setText(f'{pv.settings['components'][component]['default']:.{self.floatdp}f}')
            # self.slider.setEnabled(True)
        else:
            # if blocks share the same values, populate these in the inspector
            self.slider.setValue(0)
            commonValue, commonMin, commonMax, commonDefault, commonMagnitudeState = True, True, True, True, True
            for block in shared.activeEditor.area.selectedBlocks[1:]:
                if commonValue and block.settings['components'][self.component]['value'] != shared.activeEditor.area.selectedBlocks[0].settings['components'][self.component]['value']:
                    commonValue = False
                if commonMin and block.settings['components'][self.component]['min'] != shared.activeEditor.area.selectedBlocks[0].settings['components'][self.component]['min']:
                    commonMin = False
                if commonMax and block.settings['components'][self.component]['max'] != shared.activeEditor.area.selectedBlocks[0].settings['components'][self.component]['max']:
                    commonMax = False
                if commonDefault and block.settings['components'][self.component]['default'] != shared.activeEditor.area.selectedBlocks[0].settings['components'][self.component]['default']:
                    commonDefault = False
                if commonMagnitudeState and block.settings['magnitudeOnly'] != shared.activeEditor.area.selectedBlocks[0].settings['magnitudeOnly']:
                    commonMagnitudeState = False
                
            self.value.setText('--') if not commonValue else self.value.setText(f'{shared.activeEditor.area.selectedBlocks[0].settings['components'][self.component]['value']:.3f}')
            self.minimum.setText('--') if not commonMin else self.minimum.setText(f'{shared.activeEditor.area.selectedBlocks[0].settings['components'][self.component]['min']:.3f}')
            self.maximum.setText('--') if not commonMax else self.maximum.setText(f'{shared.activeEditor.area.selectedBlocks[0].settings['components'][self.component]['max']:.3f}')
            self.default.setText('--') if not commonDefault else self.default.setText(f'{shared.activeEditor.area.selectedBlocks[0].settings['components'][self.component]['default']:.3f}')
            self.magnitudeState.setText('--') if not commonMagnitudeState else self.magnitudeState.setText('Yes' if shared.activeEditor.area.selectedBlocks[0].settings['magnitudeOnly'] else 'No')
            self.slider.setEnabled(False) if not commonMin or not commonMax else self.slider.setEnabled(True)
        self.slider.blockSignals(False)

        # Add rows
        self.layout().addWidget(self.sliderRow)
        if not self.hideRange:
            self.layout().addWidget(self.minimumRow)
            self.layout().addWidget(self.maximumRow)
            self.layout().addWidget(self.defaultRow)
        self.layout().addWidget(self.advanced)
        self.layout().addWidget(self.magnitudeRow)
        # Apply colors
        self.UpdateColors()

    def ToggleMagnitudeState(self):
        if shared.activeEditor.area.multipleBlocksSelected and self.magnitudeState.text() == '--':
            shared.activeEditor.area.selectedBlocks[0].settings['magnitudeOnly'] = False
        originalState = shared.activeEditor.area.selectedBlocks[0].settings['magnitudeOnly']
        for block in shared.activeEditor.area.selectedBlocks:
            block.settings['magnitudeOnly'] = not originalState
        if originalState:
            self.magnitudeState.setText('No')
        else:
            self.magnitudeState.setText('Yes')

    def UpdatePVSetValueCheck(self):
        for block in shared.activeEditor.area.selectedBlocks:
            if hasattr(block, 'set'):
                block.set.setText(self.value.text())

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
        for block in shared.activeEditor.area.selectedBlocks:
            if 'valueType' not in block.settings['components'][self.component].keys():
                block.settings['components'][self.component]['valueType'] = float
            block.settings['components'][self.component]['value'] = block.settings['components'][self.component]['valueType'](v)
            if 'linkedElement' in block.settings:
                block.UpdateLinkedElement(self.slider, self.ToAbsolute)
            else:
                if block.type in block.pvBlockTypes:
                    block.data[0] = v

    def SetSliderValue(self):
        rangeSpecified = self.minimum.text() != '--' and self.maximum.text() != '--'
        self.value.clearFocus()
        v = float(self.value.text())
        v = v if abs(v) > self.eps else 0
        self.value.setText(f'{v:.3f}')
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
        if not shared.activeEditor.area.multipleBlocksSelected:
            self.UpdateSlider()
        else:
            for block in shared.activeEditor.area.selectedBlocks:
                if 'valueType' not in self.pv.settings['components'][self.component].keys():
                    block.settings['components'][self.component]['valueType'] = float
                block.settings['components'][self.component]['value'] = max(min(block.settings['components'][self.component]['valueType'](self.value.text()), block.settings['components'][self.component]['max']), block.settings['components'][self.component]['min'])
                if hasattr(block, 'set'):
                    block.set.setText(f'{block.settings['components'][self.component]['value']:.3f}')
            if rangeSpecified:
                self.slider.blockSignals(True)
                self.UpdateSlider()
                self.slider.blockSignals(False)

    def UpdateSlider(self):
        newValue = float(self.value.text())
        self.slider.setValue(self.ToSliderValue(newValue))
        if 'linkedElement' in self.pv.settings:
            self.pv.UpdateLinkedElement(self.slider, self.ToAbsolute)
        else:
            self.pv.data[0] = self.ToAbsolute(self.slider.value())

    def Reset(self):
        if self.default.text() != '--':
            default = float(self.default.text())
            default = default if abs(default) > self.eps else 0
            self.slider.setValue(self.ToSliderValue(default))
        for block in shared.activeEditor.area.selectedBlocks:
            if 'linkedElement' in block.settings:
                block.UpdateLinkedElement(self.slider, self.ToAbsolute)
            else:
                block.data[0] = self.ToAbsolute(self.slider.value())
            block.settings['components'][self.component]['value'] = block.settings['components'][self.component]['default']
            if hasattr(block, 'set'):
                block.set.setText(f'{block.settings['components'][self.component]['value']:.3f}')
        if shared.activeEditor.area.multipleBlocksSelected:
            shared.workspace.assistant.PushMessage(f'Reset {self.component.capitalize()} component on {len(shared.activeEditor.area.selectedBlocks)} blocks.')
        else:
            shared.workspace.assistant.PushMessage(f'Reset {self.component.capitalize()} component on {self.pv.name}.')

    def SetDefault(self, override = False):
        if not override:
            self.default.clearFocus()
            v = float(self.default.text())
            v = v if abs(v) > self.eps else 0
            for block in shared.activeEditor.area.selectedBlocks:
                block.settings['components'][self.component]['default'] = max(min(v, block.settings['components'][self.component]['max']), block.settings['components'][self.component]['min'])
            self.default.setText(f'{v:.{self.floatdp}f}')
            if shared.activeEditor.area.multipleBlocksSelected:
                shared.workspace.assistant.PushMessage(f'Updated default of {self.component.capitalize()} component on {len(shared.activeEditor.area.selectedBlocks)} blocks.')
            else:
                shared.workspace.assistant.PushMessage(f'Updated default of {self.component.capitalize()} component on {self.pv.name}.')
        
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

    def SetMinimum(self, override = False):
        '''`override` is a bool. Component should be updated before calling this override. '''
        rangeSpecified = self.minimum.text() != '--' and self.maximum.text() != '--'
        if not override:
            self.minimum.clearFocus()
            v = float(self.minimum.text())
            for block in shared.activeEditor.area.selectedBlocks:
                if v >= block.settings['components'][self.component]['max']:
                    continue
                block.settings['components'][self.component]['min'] = v
                block.settings['components'][self.component]['default'] = max(v, block.settings['components'][self.component]['default'])
            if rangeSpecified:
                if self.default.text() != '--':
                    default = max(v, float(self.default.text()))
                    formattedDefault = default if abs(default) > self.eps else 0
                    self.default.setText(f'{formattedDefault:.{self.floatdp}f}')
                    for block in shared.activeEditor.area.selectedBlocks:
                        block.settings['components'][self.component]['default'] = default
                self.range = block.settings['components'][self.component]['max'] - v
                newSliderValue = max(float(self.value.text()), v) if self.value.text() != '--' else block.settings['components']['value']['min'] + .5 * self.range
                formattedValue = newSliderValue if abs(newSliderValue) > self.eps else 0
                self.value.setText(f'{formattedValue:.{self.floatdp}f}')
                self.slider.blockSignals(True)
                self.slider.setValue(self.ToSliderValue(formattedValue))
                self.slider.blockSignals(False)
            if shared.activeEditor.area.multipleBlocksSelected:
                for block in shared.activeEditor.area.selectedBlocks:
                    block.settings['components'][self.component]['value'] = max(block.settings['components'][self.component]['value'], v)
                    if hasattr(block, 'set'):
                        block.set.setText(f'{block.settings['components'][self.component]['value']:.3f}')
            # else:
            #     self.slider.setValue(self.ToSliderValue(formattedValue))
            formattedMin = v if abs(v) > self.eps else 0
            self.minimum.setText(f'{formattedMin:.{self.floatdp}f}')
        elif not shared.activeEditor.area.multipleBlocksSelected:
            self.range = 1
            self.slider.setRange(0, self.pv.settings['components'][self.component]['max'] - self.pv.settings['components'][self.component]['min'] - 1)
            newSliderValue = max(self.pv.settings['components'][self.component]['value'], self.pv.settings['components'][self.component]['min'])
            self.pv.settings['components'][self.component]['value'] = newSliderValue
            self.slider.setValue(self.ToSliderValue(newSliderValue))

        if not self.hideRange and not shared.activeEditor.area.multipleBlocksSelected: # blinking cursor error in proxy widgets, so redraw the line edit.
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
        if not shared.activeEditor.area.multipleBlocksSelected:
            self.UpdatePVSetValueCheck()
            shared.workspace.assistant.PushMessage(f'Updated minimum of {self.component.capitalize()} component on {self.pv.name}.')
        else:
            shared.workspace.assistant.PushMessage(f'Updated minimum of {self.component.capitalize()} component on {len(shared.activeEditor.area.selectedBlocks)} blocks.')
        self.slider.setEnabled(True) if rangeSpecified else self.slider.setEnabled(False)
    
    def SetMaximum(self, override = False):
        '''`override` is a bool. Component should be updated before calling this override. '''
        rangeSpecified = self.minimum.text() != '--' and self.maximum.text() != '--'
        if not override:
            self.maximum.clearFocus()
            v = float(self.maximum.text())
            for block in shared.activeEditor.area.selectedBlocks:
                if v <= block.settings['components'][self.component]['min']:
                    continue
                block.settings['components'][self.component]['max'] = v
                block.settings['components'][self.component]['default'] = min(v, block.settings['components'][self.component]['default'])
            if rangeSpecified:
                if self.default.text() != '--':
                    default = min(v, float(self.default.text()))
                    formattedDefault = default if abs(default) > self.eps else 0
                    self.default.setText(f'{formattedDefault:.{self.floatdp}f}')
                    for block in shared.activeEditor.area.selectedBlocks:
                        block.settings['components'][self.component]['default'] = default
                self.range = v - block.settings['components'][self.component]['min']
                self.maximum.setText(f'{v:.{self.floatdp}f}')
                newSliderValue = min(float(self.value.text()), v) if self.value.text() != '--' else block.settings['components'][self.component]['min'] + .5 * self.range
                formattedValue = newSliderValue if abs(newSliderValue) > self.eps else 0
                self.value.setText(f'{formattedValue:.{self.floatdp}f}')
                self.slider.blockSignals(True)
                self.slider.setValue(self.ToSliderValue(formattedValue))
                self.slider.blockSignals(False)
                if shared.activeEditor.area.multipleBlocksSelected:
                    for block in shared.activeEditor.area.selectedBlocks:
                        block.settings['components'][self.component]['value'] = min(block.settings['components'][self.component]['value'], v)
                        if hasattr(block, 'set'):
                            block.set.setText(f'{block.settings['components'][self.component]['value']:.3f}')
                # else:
                #     self.slider.setValue(self.ToSliderValue(formattedValue))
        elif not shared.activeEditor.area.multipleBlocksSelected:
            self.range = 1
            self.slider.setRange(0, self.pv.settings['components'][self.component]['max'] - 1)
            newSliderValue = min(self.pv.settings['components'][self.component]['value'], self.pv.settings['components'][self.component]['max'])
            self.pv.settings['components'][self.component]['value'] = newSliderValue
            self.slider.setValue(self.ToSliderValue(newSliderValue)) # assign the value of the slider
        
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
        if not shared.activeEditor.area.multipleBlocksSelected:
            self.UpdatePVSetValueCheck()
            shared.workspace.assistant.PushMessage(f'Updated maximum of {self.component.capitalize()} component on {self.pv.name}.')
        else:
            shared.workspace.assistant.PushMessage(f'Updated maximum of {self.component.capitalize()} component on {len(shared.activeEditor.area.selectedBlocks)} blocks.')
        self.slider.setEnabled(True) if rangeSpecified else self.slider.setEnabled(False)

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
        self.value.setStyleSheet(style.LineEditStyle(color = '#222222', bold = True, fontColor = '#c4c4c4', paddingLeft = self.paddingLeft, paddingBottom = 0))
        if not self.hideRange:
            self.minimum.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = self.paddingLeft, paddingBottom = 0))
            self.maximum.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = self.paddingLeft, paddingBottom = 0))
            self.default.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = self.paddingLeft, paddingBottom = 0))
            self.minimumLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
            self.maximumLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
            self.defaultLabel.setStyleSheet(style.LabelStyle(fontColor = '#c4c4c4'))
        self.advancedLabel.setStyleSheet(style.LabelStyle(fontColor = '#d44931', bold = True, underline = True))
        self.magnitudeLabel.setStyleSheet(style.LabelStyle(fontColor = "#c4c4c4"))
        self.magnitudeState.setStyleSheet(style.LineEditStyle(color = '#222222', fontColor = '#c4c4c4', paddingLeft = 0, paddingBottom = 0))
        self.magnitudeSwitch.setStyleSheet(style.PushButtonStyle(color = '#2e2e2e', hoverColor = '#3e3e3e', fontColor = '#c4c4c4', padding = 5))
        self.resetButton.setStyleSheet(style.PushButtonStyle(color = '#2e2e2e', hoverColor = '#3e3e3e', fontColor = '#c4c4c4', padding = 5))