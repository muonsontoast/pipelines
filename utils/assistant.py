from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QTimer

class Assistant:
    def __init__(self, messageTitle: QLabel, messageTimeout = 10):
        super().__init__()
        self.defaultMessage = 'Assistant: '
        self.message = 'Assistant: '
        self.messageTitle = messageTitle
        self.messageTimeout = messageTimeout * 1e3

    def PushMessage(self, message, messageType: str = 'Normal'):
        '''`message` can be of types <Normal/Warning/Error/Critical Error>'''
        prefix = ''
        if messageType in ['Warning', 'Error', 'Critical Error']:
            prefix = f'[{messageType}] '
        self.message = f'Assistant: {prefix}{message}'
        self.Review() # immediately update the message
        self.timer.stop()
        self.timer.start(self.messageTimeout)

    def ClearMessage(self):
        self.message = 'Assistant: '

    def Review(self):
        self.messageTitle.setText(self.message)
        if self.message != self.defaultMessage:
            self.message = self.defaultMessage

    def Start(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.Review)
        self.timer.start(self.messageTimeout)