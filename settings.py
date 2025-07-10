from PySide6.QtWidgets import QWidget, QFrame, QLabel, QLineEdit, QSlider, QCheckBox, QGridLayout, QHBoxLayout, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt

class Settings(QFrame):
    def __init__(self, window):
          super().__init__()
          self.parent = window
          self.setLayout(QVBoxLayout())
          self.setContentsMargins(0, 0, 0, 0)
          self.settings = dict()

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings

def CreateSettingElement(name, *args, **kwargs):
        '''Returns *element* to be created, plus an additional *settingElement* which houses it and its name if one is specified.\n
        A list of `*args` elements for the settingElement.\n
        Set `subElementWidget` to allow settingElementChecking.'''
        alignment = kwargs.get('alignment', Qt.AlignLeft)
        subElementWidget = kwargs.get('subElementWidget')
        names = kwargs.get('names', [])
        numNames = len(names)

        settingElement = QFrame()
        # settingElement.setMaximumHeight(100)
        settingElementLayout = QGridLayout(settingElement)
        settingElementLayout.setSpacing(4)
        settingElementLayout.setContentsMargins(5, 5, 0, 0)
        settingElementTitle = QLabel(f'<b>{name}<\b>')
        settingElementLayout.addWidget(settingElementTitle, 0, 0)

        for _, element in enumerate(args):
            if type(element) == QCheckBox:
                if subElementWidget is not None:
                    element.clicked.connect(lambda _: ToggleHysteresisCompensation(_, subElementWidget))

            if type(element) == QLineEdit:
                element.returnPressed.connect(lambda: element.clearFocus())
                element.setAlignment(Qt.AlignCenter)
                spacerWidget = QWidget()
                spacerWidgetLayout = QHBoxLayout(spacerWidget)
                spacerWidgetLayout.setContentsMargins(*kwargs.get('contentMargin', (5, 0, 20, 5)))
                spacerWidget.setMinimumWidth(100)
                spacerWidget.setMaximumWidth(400)
                if _ < numNames:
                    spacerWidgetLayout.addWidget(QLabel(names[_]), alignment = Qt.AlignLeft)
                spacerWidgetLayout.addWidget(element, alignment = alignment)
                settingElementLayout.addWidget(spacerWidget, _ + 1, 0)
            elif type(element) == QSlider:
                sliderBoxSlider = QSlider(Qt.Horizontal)
                sliderBoxSlider.setMinimum(kwargs.get('sliderMin', 5))
                sliderBoxSlider.setMaximum(kwargs.get('sliderMax', 500))
                sliderBoxSlider.setValue(20)
                sliderBoxValue = QLineEdit('20')
                sliderBoxValue.setFixedWidth(65)
                sliderBoxValue.setAlignment(Qt.AlignCenter)
                window = kwargs.get('window', None)
                if window is not None:
                    window.__setattr__(name.replace(' ', '') + 'Value', sliderBoxValue)
                spacerWidget = QWidget()
                spacerWidgetLayout = QHBoxLayout(spacerWidget)
                spacerWidgetLayout.setContentsMargins(*kwargs.get('contentMargin', (5, 0, 10, 5)))
                if _ < numNames:
                    spacerWidgetLayout.addWidget(QLabel(names[_]))
                spacerWidgetLayout.addWidget(sliderBoxSlider)
                spacerWidgetLayout.addWidget(sliderBoxValue)
                settingElementLayout.addWidget(spacerWidget, _ + 1, 0, alignment = alignment)
            elif type(element) == QCheckBox:
                spacerWidget = QWidget()
                spacerWidgetLayout = QHBoxLayout(spacerWidget)
                spacerWidgetLayout.setContentsMargins(*kwargs.get('contentMargin', (5, 0, 10, 5)))
                if _ < numNames:
                    spacerWidgetLayout.addWidget(QLabel(names[_]))
                spacerWidgetLayout.addWidget(element)
                settingElementLayout.addWidget(spacerWidget, _ + 1, 0, alignment = alignment)
            else:
                spacerWidget = QWidget()
                # spacerWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                spacerWidgetLayout = QHBoxLayout(spacerWidget)
                spacerWidgetLayout.setContentsMargins(*kwargs.get('contentMargin', (5, 0, 20, 5)))
                if _ < numNames:
                    spacerWidgetLayout.addWidget(QLabel(names[_]))
                element.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
                spacerWidgetLayout.addWidget(element)
                settingElementLayout.addWidget(spacerWidget, _ + 1, 0, alignment = alignment)
        
        return settingElement

def ToggleHysteresisCompensation(v, settingSubElementWidget):
        settingSubElementWidget.setEnabled(v)