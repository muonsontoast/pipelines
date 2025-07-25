from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsProxyWidget
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap, QImage
from .. import shared
import os

class RunningCircle(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.label)
        self.running = False
        self.frames = []
        self.numFrames = 119
        self.frameSize = 30
        self.setFixedSize(self.frameSize, self.frameSize)
        color = 'black' if shared.lightModeOn else 'grey'

        print('Loading running circle frames into memory')
        # Load the frames into memory
        for _ in range(self.numFrames):
            path = os.path.join(shared.runningCircleFolder, f'running/{color}/{_}.png')
            frame = QImage(path)
            scaledFrame = frame.scaled(
                self.frameSize, self.frameSize,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )
            scaledFrame = QPixmap.fromImage(scaledFrame)
            scaledFrame.setDevicePixelRatio(1.0)
            self.frames.append(scaledFrame)
        print('Finished loading running circle frames into memory')

        self.currentFrame = 0
        self.label.setPixmap(self.frames[self.currentFrame])
        self.CreateTimer()
        self.label.setVisible(False)

    def Stop(self):
        self.running = False
        self.label.setVisible(False)
        self.timer.stop()
    
    def Start(self, timeout = 15):
        # default refresh rate is 60 fps / 15 ms
        self.running = True
        self.label.setVisible(True)
        self.timer.start(timeout)

    def CreateTimer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.UpdateFrame)

    def UpdateFrame(self):
        self.currentFrame = (self.currentFrame + 1) % self.numFrames
        self.label.setPixmap(self.frames[self.currentFrame])