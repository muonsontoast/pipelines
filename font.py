from PySide6.QtGui import QFont
from . import style

def SetFontSpacing(widget, spacing):
    '''Specify a QWidget `widget` and `spacing` as a percentage (100 is nominal).'''
    font = widget.font()
    font.setLetterSpacing(QFont.PercentageSpacing, spacing)
    widget.setFont(font)

def SetFontToBold(widget):
    font = widget.font()
    font.setBold(True)
    widget.setFont(font)

def SetFontSize(label, size):
    label.setStyleSheet(f'''
    QLabel {{
    background-color: transparent;
    color: {style.fontColor};
    font-size: {size}px;
    font-family: {style.fontFamily};
    padding-left: 10px;
    }}''')