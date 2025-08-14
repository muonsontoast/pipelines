from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import QTimer, Qt
from .. import shared

class RunningCircle(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.label)
        self.running = False
        self.stop = False
        self.setFixedSize(shared.runningCircleResolution + 10, shared.runningCircleResolution + 10)
        self.currentFrame = 0
        self.CreateTimer()
        self.label.setVisible(True)

    def Stop(self):
        self.running = False
        self.label.setVisible(False)
        self.stop = False
    
    def Start(self, timeout = 15):
        # default refresh rate is 60 fps / 15 ms
        self.running = True
        self.label.setVisible(True)
        self.timer.start(timeout)

    def CreateTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.UpdateFrame)

    def UpdateFrame(self):
        if self.stop:
            self.Stop()
        self.currentFrame = (self.currentFrame + 1) % shared.runningCircleNumFrames
        self.label.setPixmap(shared.runningCircleFrames[self.currentFrame])