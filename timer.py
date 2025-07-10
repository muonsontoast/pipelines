from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QPalette, QColor

class Timer(QObject):
    '''A worker that will periodically check for updates from a process or processes.'''
    def __init__(self, interval = 200, progressBar = None, statusText = None, monitor = None, scanner = None, f = True):
        '''An interval in ms.'''
        super().__init__()
        self.monitor = monitor
        self.scanner = scanner
        self.timer = QTimer(self)
        self.timer.setInterval(interval)
        self.canDeleteSafely = False
        if f:
            self.timer.timeout.connect(self.PassScanDataToMonitor)
        else:
            self.timer.timeout.connect(self.Dummy)
        self.progressBar = progressBar
        self.statusText = statusText

    def Dummy(self):
        if not self.scanner.pauseScan:
            self.scanner.steps += 1
            self.scanner.dataDict['steps'] += 1

    def PassScanDataToMonitor(self):
        if not self.scanner.working:
            return
        self.monitor.UpdatePlot(self.scanner.dataDict)
        if self.scanner.steps == self.scanner.numSteps:
            self.statusText.setText('Status: Scan Complete')
            self.progressBar.setValue(self.scanner.steps / self.scanner.numSteps * 100)
            palette = self.progressBar.palette()
            palette.setColor(QPalette.Highlight, QColor("#11b841"))  # background color of the bar
            self.progressBar.setPalette(palette)
            self.scanner.steps = 0
            self.scanner.pauseScan = False
            self.scanner.stopScan = False
            self.scanner.working = False
            self.canDeleteSafely = True
            self.scanner.parent.CleanupTimers()
        elif self.scanner.stopScan:
            self.statusText.setText('Status: Scan Stopped')
            self.progressBar.setValue(0)
            self.scanner.steps = 0
            self.scanner.pauseScan = False
            self.scanner.stopScan = False
            self.scanner.working = False
            self.canDeleteSafely = True
        elif self.scanner.pauseScan:
            self.statusText.setText('Status: Scan Paused')
        else:
            self.progressBar.setValue(self.scanner.steps / self.scanner.numSteps * 100)
            self.statusText.setText('Status: Scanning')

