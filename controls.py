from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QPushButton, QCheckBox, QCompleter, QLineEdit,
    QSpacerItem, QMessageBox, QGridLayout, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPalette, QColor
from .settings import CreateSettingElement
from .scan import Scanner
from .timer import Timer

class Controls(QWidget):
    '''A window containing many useful utility functions and commonly performed accelerator operations.\n'''
    def __init__(self, window, **kwargs):
        '''`window` is the application instantiating this control window.\n
        Accepts **kwargs**:\n
        `gridSteps` is a list of step sizes in each dimension of a grid search.\n
        '''
        super().__init__()
        self.parent = window
        self.screenWidth = window.size().width()
        self.screenHeight = window.size().height()
        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(QGridLayout())
        self.setFixedSize(.2 * self.screenWidth, .78 * self.screenHeight)
        self.online = False
        self.saveData = True
        self.name = f'CONTROL PANEL {kwargs.get('idx', 0)}'
        # Link to the most recently opened monitor by default (but this can be changed later)
        self.linkedMonitor = None
        if len(self.parent.monitors) > 0:
            self.linkedMonitor = list(self.parent.monitors.values())[-1]

        self.ReDraw()

    def ReDraw(self):
        self.Clear()
        # Draw the outer frame
        self.frame = QFrame()
        self.frame.setLayout(QGridLayout())
        self.frame.setFrameShape(QFrame.Box)
        self.frame.setContentsMargins(1, 1, 1, 1) # small padding
        self.layout().addWidget(self.frame)
        self.dialogResponse = False
        # Add a title
        label = QLabel(f'<b>{' '.join(self.name.split(' ')[:2])}<\b>')
        label.setStyleSheet('font-size: 18px')
        self.frame.layout().addWidget(label, 0, 0)
        # Add a monitor selector
        completer = QCompleter([monitor.name for monitor in self.parent.monitors.values()])
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.monitorSelector = QLineEdit(self.linkedMonitor.name) if self.linkedMonitor is not None else QLineEdit('None')
        self.monitorSelector.setAlignment(Qt.AlignCenter)
        self.monitorSelector.setCompleter(completer)
        self.monitorSelector.returnPressed.connect(lambda: self.SelectMonitor(self.monitorSelector.text()))
        self.onlineCheckWidget = QWidget()
        self.onlineCheckWidget.setLayout(QHBoxLayout())
        self.onlineCheckWidget.layout().addWidget(QLabel('<b>Online</b>'))
        self.onlineCheck = QCheckBox()
        self.onlineCheck.clicked.connect(self.ToggleOnlineCheck)
        self.onlineCheck.setChecked(self.online)
        self.onlineCheckWidget.layout().addWidget(self.onlineCheck, alignment = Qt.AlignRight)
        self.frame.layout().addWidget(self.onlineCheckWidget, 4, 0)
        # Monitor housing (name and selector)
        monitorSelectorHousing = QFrame()
        monitorSelectorHousing.setLayout(QHBoxLayout())
        monitorSelectorHousing.layout().addWidget(QLabel('<b>Connected to:</b>'))
        monitorSelectorHousing.layout().addWidget(self.monitorSelector, alignment = Qt.AlignRight)
        self.frame.layout().addWidget(monitorSelectorHousing, 1, 0)
        # Scan section
        scanSection = QFrame()
        scanSection.setFrameShape(QFrame.Box)
        scanSection.setLayout(QHBoxLayout())
        scanSection.setContentsMargins(1, 1, 1, 1)
        startScanButton = QPushButton('Start')
        startScanButton.pressed.connect(self.StartScan)
        self.pauseScanButton = QPushButton('Pause')
        self.pauseScanButton.pressed.connect(self.PauseScan)
        stopScanButton = QPushButton('Stop')
        stopScanButton.pressed.connect(self.StopScan)
        scanSection.layout().addWidget(startScanButton)
        scanSection.layout().addWidget(self.pauseScanButton)
        scanSection.layout().addWidget(stopScanButton)
        scanSectionHousing = CreateSettingElement('Scan', scanSection)
        for button in scanSectionHousing.findChildren(QPushButton):
            button.setFixedHeight(.075 * self.screenHeight)
        scanSectionHousing.setContentsMargins(5, 5, 5, 5)
        self.frame.layout().addWidget(scanSectionHousing, 2, 0)
        # Optimise section
        optimiserSection = QFrame()
        optimiserSection.setContentsMargins(1, 1, 1, 1)
        optimiserSection.setFrameShape(QFrame.Box)
        optimiserSection.setLayout(QHBoxLayout())
        optimiserSection.layout().setSpacing(.01 * self.screenHeight)
        startOptimiserButton = QPushButton('Start')
        startOptimiserButton.pressed.connect(self.StartOptimiser)
        pauseOptimiserButton = QPushButton('Pause')
        pauseOptimiserButton.pressed.connect(self.PauseOptimiser)
        stopOptimiserButton = QPushButton('Stop')
        stopOptimiserButton.pressed.connect(self.StopOptimiser)
        optimiserSection.layout().addWidget(startOptimiserButton)
        optimiserSection.layout().addWidget(pauseOptimiserButton)
        optimiserSection.layout().addWidget(stopOptimiserButton)
        optimiserSectionHousing = CreateSettingElement('Optimiser', optimiserSection)
        for button in optimiserSectionHousing.findChildren(QPushButton):
            button.setFixedHeight(.075 * self.screenHeight)
        optimiserSectionHousing.setContentsMargins(5, 5, 5, 5)
        self.frame.layout().addWidget(optimiserSectionHousing, 3, 0)
        # Record data from operations
        self.saveDataCheckWidget = QWidget()
        self.saveDataCheckWidget.setLayout(QHBoxLayout())
        self.saveDataCheckWidget.layout().addWidget(QLabel('<b>Save Data</b>'))
        self.saveDataCheck = QCheckBox()
        self.saveDataCheck.clicked.connect(self.ToggleSaveDataCheck)
        self.saveDataCheck.setChecked(self.saveData)
        self.saveDataCheckWidget.layout().addWidget(self.saveDataCheck, alignment = Qt.AlignRight)
        self.frame.layout().addWidget(self.saveDataCheckWidget, 5, 0)
        # Add stretch at the end if the widgets don't automatically fill all the space
        self.frame.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding), 6, 0)

    def DisplayFailDialog(self, content, title):
        messageBox = QMessageBox()
        messageBox.setWindowTitle(title)
        messageBox.setText(content)
        messageBox.setIcon(QMessageBox.Critical)
        messageBox.setWindowIcon(self.parent.parent.windowIcon())
        messageBox.setStandardButtons(QMessageBox.Ok)

        result = messageBox.exec()

    def DisplayWarningDialog(self, content, title):
        messageBox = QMessageBox()
        messageBox.setWindowTitle(title)
        messageBox.setText(content)
        messageBox.setIcon(QMessageBox.Warning)
        messageBox.setWindowIcon(self.parent.parent.windowIcon())
        messageBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        result = messageBox.exec()
        if result == QMessageBox.No:
            return False
        return True
    
    def StartScan(self):
        if self.linkedMonitor is None:
            return
        if hasattr(self, 'scanner'):
            if self.scanner.working:
                return
        self.scanner = Scanner(self, self.linkedMonitor.scanSteps)
        if hasattr(self.scanner, 'dummyTimer'):
            self.scanner.dummyTimer.timer.stop()
            self.scanner.dummyTimer.deleteLater()
            del self.scanner.dummyTimer
        QApplication.processEvents()
        palette = self.parent.parent.progressBar.palette()
        palette.setColor(QPalette.Highlight, QColor("#3b84f2"))  # background color of the bar
        self.parent.parent.progressBar.setPalette(palette)
        self.scanner.AttemptToScan()

    def PauseScan(self):
        if not self.scanner.working:
            return
        self.pauseScanButton.setText('Resume') if not self.scanner.pauseScan else self.pauseScanButton.setText('Pause')
        self.scanner.pauseScan = not self.scanner.pauseScan # toggle

    def StopScan(self):
        self.scanner.stopScan = True
        self.pauseScanButton.setText('Pause')
        self.CleanupTimers()
    
    def CleanupTimers(self):
        if hasattr(self.scanner, 'dummyTimer'):
            self.scanner.dummyTimer.timer.stop()
            self.scanner.dummyTimer.deleteLater()
            del self.scanner.dummyTimer
        QApplication.processEvents()
        # Create a short-lived timer to check to wait unitl the main timer has finished.
        self.safeDeleteTimer =  QTimer(self)
        self.safeDeleteTimer.setInterval(50)
        self.safeDeleteTimer.timeout.connect(self.CheckMainTimerStatus)
        self.safeDeleteTimer.start()

    def CheckMainTimerStatus(self):
        if not hasattr(self.scanner, 'timer'):
            self.safeDeleteTimer.stop()
            self.safeDeleteTimer.deleteLater()
            del self.safeDeleteTimer
        elif self.scanner.timer.canDeleteSafely:
            self.safeDeleteTimer.stop()
            self.safeDeleteTimer.deleteLater()
            self.scanner.timer.timer.stop()
            self.scanner.timer.deleteLater()
            del self.scanner.timer
            del self.safeDeleteTimer
        QApplication.processEvents()

    def StartOptimiser(self):
        pass

    def PauseOptimiser(self):
        pass

    def StopOptimiser(self):
        pass

    def ToggleSaveDataCheck(self, v):
        self.saveData = v

    def ToggleOnlineCheck(self, v):
        self.online = v

    def SelectMonitor(self, name):
        if name in self.parent.monitors.keys():
            self.linkedMonitor = self.parent.monitors[name]
        self.monitorSelector.clearFocus()

    def Clear(self):
        for widget in self.findChildren(QWidget):
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()