from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QTimer

class Assistant:
    def __init__(self, messageTitle: QLabel, messageTimeout = 10):
        super().__init__()
        self.defaultMessage = 'Assistant: '
        self.message = 'Assistant: '
        self.messageTitle = messageTitle
        self.messageTimeout = messageTimeout * 1e3
        self.ignoreRequests = False

    def PushMessage(self, message, messageType: str = 'Normal'):
        '''`message` can be of types <Normal/Warning/Error/Critical Error>'''
        if self.ignoreRequests:
            return
        prefix = ''
        spanPrefix = ''
        spanSuffix = ''
        if messageType in ['Warning', 'Error', 'Critical Error']:
            if messageType == 'Warning':
                spanPrefix = '<span style = "color: #FF8811;">'
            elif messageType == 'Error':
                spanPrefix = '<span style = "color: #C6242F;">'
            else:
                spanPrefix = '<span style = "color: #800E13;">'
            
            spanSuffix = '</span>'
            prefix = rf'[<b>{spanPrefix}{messageType.upper()}{spanSuffix}</b>] '
        self.message = rf'Assistant: {prefix}{message}'
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