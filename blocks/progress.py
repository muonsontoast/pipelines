from PySide6.QtWidgets import QWidget

class Progress(QWidget):
    '''A progress bar for actionable blocks to be added to .widget on the entity.'''
    def __init__(self, **kwargs):
        '''Accepts kwargs: `color`, `backgroundColor`, `height`.'''
        color = kwargs.pop('color', '#c4c4c4')
        backgroundColor = kwargs.pop('backgroundColor', '#2e2e2e')
        borderRadius = 6;
        self.setFixedHeight()
        self.layout()