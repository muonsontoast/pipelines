from PySide6.QtGui import QColor
from . import shared

backgroundColor = '#181818'
tabColor = '#282523'
PVSelectedColor = '#74BC80'
tabSelectedColor = '#c4c4c4'
tabHoverColor = '#303F33'
buttonColor = '#1E1E1E'
buttonSelectedColor = '#313131'
buttonHoverColor = '#252525'
buttonBorderColor = '#141414'
editorButtonColor = '#5B4981'
inspectorExpandableColor = '#342D2A'
inspectorNameBackgroundColor = '#407549'
fontColor = '#C4C4C4'
checkColor = '#5B4981'
fontSize = '12px'
fontFamily = 'Roboto'

# Light color theme.
light01 = {
'backgroundColor': '#E4D9CA',
'tabColor': '#282523',
'tabHoverColor': '#303F33',
'tabSelectedColor': '#3F5142',
'buttonColor': '#1e1e1e',
'buttonSelectedColor': '#313131',
'buttonHoverColor': '#252525',
'buttonBorderColor': '#141414',
'editorButtonColor': '#5b4981',
'inspectorExpandableColor': '#342d2a',
'inspectorNameBackgroundColor': '#407549',
'fontColor': '#1e1e1e',
'checkColor': '#5b4981',
'fontSize': '12px',
'fontFamily': 'Roboto',
}

dark01 = {
'backgroundColor': '#181818',
'tabColor': '#282523',
'tabHoverColor': '#303f33',
'tabSelectedColor': '#513f3f',
'buttonColor': '#1e1e1e',
'buttonSelectedColor': '#313131',
'buttonHoverColor': '#252525',
'buttonBorderColor': '#141414',
'inspectorExpandableColor': '#5b4981',
'inspectorNameBackgroundColor': '#407549',
'fontColor': '#1e1e1e',
'fontSize': '12px',
'fontFamily': 'Roboto',
}

def WidgetStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `borderRadius`, `borderRadius<TopLeft/TopRight/BottomRight/BottomLeft>`, `borderThickness`, `borderColor`, `borders` = list(<left/top/right/down> (str)), `marginLeft`, `marginRight`, `fontColor`, `fontSize`, `fontFamily`'''
    borders = kwargs.get('borders', list())
    borderThickness = f'{kwargs.get('borderThickness', 2)}px solid {kwargs.get('borderColor'), 'transparent'}'
    borderRadius = kwargs.get('borderRadius', '')
    if borderRadius != '':
        borderRadius = f'''
        border-radius: {borderRadius}px;
        '''
    else:
        borderRadius = f'''
        border-top-left-radius: {kwargs.get('borderRadiusTopLeft', '0')}px;
        border-top-right-radius: {kwargs.get('borderRadiusTopRight', '0')}px;
        border-bottom-right-radius: {kwargs.get('borderRadiusBottomRight', '0')}px;
        border-bottom-left-radius: {kwargs.get('borderRadiusBottomLeft', '0')}px;
        '''
    borders = f'''
    border-left: {'none' if 'left' not in borders else borderThickness};
    border-top: {'none' if 'top' not in borders else borderThickness};
    border-right: {'none' if 'right' not in borders else borderThickness};
    border-bottom: {'none' if 'bottom' not in borders else borderThickness};
    '''
    return f'''
    QWidget {{
    background-color: {kwargs.get('color', 'transparent')};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    margin-left: {kwargs.get('marginLeft', 1)}px;
    margin-right: {kwargs.get('marginRight', 1)}px;
    {borderRadius}
    {borders}
    }}'''

def PushButtonStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `borderColor`, `borderRadius`, `hoverColor`, `padding`, `textAlign`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QPushButton {{
    background-color: {kwargs.get('color', buttonColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    padding: {kwargs.get('padding', 8)}px;
    border: 2px solid {kwargs.get('borderColor', buttonBorderColor)};
    border-radius: {kwargs.get('borderRadius', 5)}px;
    text-align: {kwargs.get('textAlign', 'center')};
    margin: 2px;
    }}
    QPushButton:hover {{
    background-color: {kwargs.get('hoverColor', buttonHoverColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    padding: {kwargs.get('padding', 8)}px;
    border: 2px solid {kwargs.get('borderColor', buttonBorderColor)};
    border-radius: {kwargs.get('borderRadius', 5)}px;
    text-align: {kwargs.get('textAlign', 'center')};
    }}'''

def PushButtonBorderlessStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `borderColor`, `hoverColor`, `fontColor`, `fontSize`, `fontFamily`, `paddingLeft`, `paddingRight`, `paddingTop`, `paddingBottom`, `marginTop`, `marginBottom`'''
    return f'''
    QPushButton {{
    background-color: {kwargs.get('color', buttonColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    padding-left: 10px;
    padding-top: {kwargs.get('paddingTop', 5)}px;
    padding-right: 10px;
    padding-bottom: {kwargs.get('paddingBottom', 5)}px;
    border: none;
    border-radius: 3px;
    margin-top: {kwargs.get('marginTop', 0)}px;
    margin-bottom: {kwargs.get('marginBottom', 0)}px;
    text-align: center;
    }}
    QPushButton:hover {{
    background-color: {kwargs.get('hoverColor', buttonHoverColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    padding-left: 10px;
    padding-top: {kwargs.get('paddingTop', 5)}px;
    padding-right: 10px;
    padding-bottom: {kwargs.get('paddingBottom', 5)}px;
    border: none;
    border-radius: 3px;
    }}''' 

def CheckStyle(**kwargs):
    return f'''
    QCheckBox::indicator {{
        background-color: {kwargs.get('color', 'transparent')};
        border: 2px solid {kwargs.get('borderColor', '#c4c4c4')};
    }}
    QCheckBox::indicator:checked {{
        background-color: {kwargs.get('checkedColor', "#848484")};
        border: 2px solid {kwargs.get('borderColor', '#c4c4c4')};
    }}'''

def InspectorSectionStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QWidget {{
    background-color: transparent;
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    text-align: left;
    border: none;
    border-radius: 0px;
    padding: 5px;
    padding-left: 5px;
    }}'''

def ToolButtonStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `hoverColor`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QToolButton {{
    background-color: {kwargs.get('color', buttonColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    padding: 5px;
    border: none;
    }}
    QToolButton:hover {{
    background-color: {kwargs.get('hoverColor', buttonHoverColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    padding: 5px;
    border: none;
    }}
    QToolButton::menu-indicator {{
    image: none;
    }}'''

def ComboStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `hoverColor`, `fontColor`, `fontSize`, `fontFamily`, `borderRadius`, `marginLeft`, `marginTop`, `marginRight`, `marginBottom`, `paddingTop`, `paddingBottom`, `paddingLeft`, `paddingRight`.'''
    return f'''
    QComboBox {{
        background-color: {kwargs.get('color', buttonColor)};
        color: {kwargs.get('fontColor', fontColor)};
        font-size: {kwargs.get('fontSize', fontSize)}px;
        font-family: {kwargs.get('fontFamily', fontFamily)};
        font-weight: bold;
        border-radius: {kwargs.get('borderRadius', 0)}px;
        border: 1px solid #6184D8;
        padding-left: {kwargs.pop('paddingLeft', 2)}px;
        padding-top: {kwargs.pop('paddingTop', 2)}px;
        padding-right: {kwargs.pop('paddingRight', 2)}px;
        padding-bottom: {kwargs.pop('paddingBottom', 2)}px;
        margin-left: {kwargs.pop('marginLeft', 2)}px;
        margin-top: {kwargs.pop('marginTop', 2)}px;
        margin-right: {kwargs.pop('marginRight', 2)}px;
        margin-bottom: {kwargs.pop('marginBottom', 2)}px;
    }}
    QComboBox::drop-down {{
        border: none;
        background: transparent;
    }}
    QComboBox QAbstractItemView {{
        color: #6184D8;
        border: 1px solid #6184D8;
        border-radius: 6px;
        padding-left: {kwargs.pop('paddingLeft', 2)}px;
        padding-top: {kwargs.pop('paddingTop', 2)}px;
        padding-right: {kwargs.pop('paddingRight', 2)}px;
        padding-bottom: {kwargs.pop('paddingBottom', 2)}px;
        margin-left: {kwargs.pop('marginLeft', 2)}px;
        margin-top: {kwargs.pop('marginTop', 2)}px;
        margin-right: {kwargs.pop('marginRight', 2)}px;
        margin-bottom: {kwargs.pop('marginBottom', 2)}px;
    }}'''

def CompleterStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `borderColor`, `borderRadius`, `hoverColor`, `paddingLeft`, `paddingRight`, `paddingBottom`, `paddingTop`, `itemSelectedColor`, `itemPadding`, `handleColor`, `bold`, `fontColor`, `fontSize`, `fontFamily`'''
    bold = 'font-weight: bold;' if kwargs.get('bold', False) else ''
    return f'''
    QListView {{
        background-color: {kwargs.get('color', '#1e1e1e')};
        color: {kwargs.get('fontColor', '#c4c4c4')};
        {bold}
        font-size: {kwargs.get('fontSize', fontSize)}px;
        font-family: {kwargs.get('fontFamily', fontFamily)};
        padding: 5px;
        padding-left: {kwargs.get('paddingLeft', 5)}px;
        padding-right: {kwargs.get('paddingRight', 5)}px;
        padding-bottom: {kwargs.get('paddingBottom', 5)}px;
        padding-top: {kwargs.get('paddingTop', 5)}px;
    }}
    QListView::item {{
        padding: {kwargs.get('itemPadding', 0)}px;
        border: none;
    }}
    QListView::item:selected {{
        background-color: {kwargs.get('itemSelectedColor', '#2e2e2e')};
        color: {kwargs.get('fontColor', '#c4c4c4')};
    }}
    QListView::item:hover {{
        background-color: {kwargs.get('itemHoverColor', '#262626')};
        color: {kwargs.get('fontColor', '#c4c4c4')};
    }}
    QScrollBar::vertical {{
        background-color: transparent;
        width: 10px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background-color: {kwargs.get('handleColor', '#3e3e3e')};
        width: 15px;
        min-height: 20px;
    }}
    QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
        background-color: transparent;
        border: none;
        width: 0px;
        height: 0px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}'''

def LineEditStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `borderColor`, `borderRadius`, `hoverColor`, `paddingLeft`, `paddingRight`, `paddingBottom`, `paddingTop`, `bold`, `fontColor`, `fontSize`, `fontFamily`'''
    bold = 'font-weight: bold;' if kwargs.get('bold', False) else ''
    return f'''
    QLineEdit {{
        background-color: {kwargs.get('color', buttonColor)};
        color: {kwargs.get('fontColor', fontColor)};
        font-size: {kwargs.get('fontSize', fontSize)}px;
        font-family: {kwargs.get('fontFamily', fontFamily)};
        {bold}
        text-align: center;
        padding-left: {kwargs.get('paddingLeft', 0)}px;
        padding-right: {kwargs.get('paddingRight', 0)}px;
        padding-bottom: {kwargs.get('paddingBottom', 0)}px;
        padding-top: {kwargs.get('paddingTop', 0)}px;
        border-radius: {kwargs.get('borderRadius', 3)};
    }}'''

def TabStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `selectedColor`, `hoverColor`, `borderRadius`, `paneColor`, `hoverColor`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QTabBar::tab {{
        background-color: {kwargs.get('color', buttonColor)};
        color: {kwargs.get('fontColor', fontColor)};
        font-size: {kwargs.get('fontSize', fontSize)}px;
        font-family: {kwargs.get('fontFamily', fontFamily)};
        font-weight: bold;
        padding-left: 10px;
        padding-top: 5px;
        padding-right: 10px;
        padding-bottom: 5px;
        margin-right: 4px;
        margin-bottom: -1px;
        border: none;
        border-radius: {kwargs.get('borderRadius', 2)};
    }}
    QTabBar::tab:selected {{
        background-color: {kwargs.get('selectedColor', buttonColor)};
        color: {kwargs.get('fontColor', fontColor)};
        font-size: {kwargs.get('fontSize', fontSize)}px;
        font-family: {kwargs.get('fontFamily', fontFamily)};
        font-weight: bold;
        padding-left: 10px;
        padding-top: 5px;
        padding-right: 10px;
        padding-bottom: 5px;
        margin-right: 4px;
        margin-bottom: -1px;
        border: none;
        border-radius: {kwargs.get('borderRadius', 2)};
    }}
    QTabBar::tab:hover {{
        background-color: {kwargs.get('hoverColor', buttonColor)};
        color: {kwargs.get('fontColor', fontColor)};
        font-size: {kwargs.get('fontSize', fontSize)}px;
        font-family: {kwargs.get('fontFamily', fontFamily)};
        font-weight: bold;
        padding-left: 10px;
        padding-top: 5px;
        padding-right: 10px;
        padding-bottom: 5px;
        margin-right: 4px;
        margin-bottom: -1px;
        border: none;
        border-radius: {kwargs.get('borderRadius', 2)};
    }}'''

def TabWidgetStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `borderRadius`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QTabWidget {{
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    border: none;
    border-radius: {kwargs.get('borderRadius', 6)};
    }}
    QTabWidget::pane {{
    background-color: {kwargs.get('color', 'transparent')};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    border: none;
    border-radius: {kwargs.get('borderRadius', 2)};
    }}
    QTabBar::pane {{
    background: transparent;
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    border: none;
    border-radius: {kwargs.get('borderRadius', 2)};
    outline: none;
    box-shadow: none;
    }}'''
    
def FrameStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `orientation`, `borderColor`, `borderTopLeftRadius`, `borderTopRightRadius`, `borderBottomRightRadius`, `borderBottomLeftRadius`, `fontColor`, `fontSize`, `fontFamily`'''
    borderColor = kwargs.get('borderColor', '')
    orientation = kwargs.get('orientation', 'right')
    border = ''
    if orientation == 'right':
        border = '' if borderColor == '' else f'border: 2px solid {borderColor}; border-width: 2px 0 2px 2px;'
    else:
        border = '' if borderColor == '' else f'border: 2px solid {borderColor}; border-width: 2px 2px 2px 0;'
    return f'''
    QFrame {{
    background-color: {kwargs.get('color', buttonColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    {border}
    border-top-left-radius: {kwargs.get('borderTopLeftRadius', 2)};
    border-top-right-radius: {kwargs.get('borderTopRightRadius', 2)};
    border-bottom-right-radius: {kwargs.get('borderBottomRightRadius', 2)};
    border-bottom-left-radius: {kwargs.get('borderBottomLeftRadius', 2)};
    }}'''

def LabelStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `textAlign`, `padding`, `borderRadius`, `bold`, `underline`, `fontColor`, `fontSize`, `fontFamily`'''
    underline = '' if not kwargs.get('underline', False) else 'text-decoration: underline;'
    bold = 'font-weight: bold;' if kwargs.get('bold', True) else ''
    return f'''
    QLabel {{
    border: none;
    background-color: {kwargs.get('color', 'none')};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    padding-left: {kwargs.get('padding', 10)}px;
    text-align: {kwargs.get('textAlign', 'center')};
    border-radius: {kwargs.get('borderRadius', 0)};
    {bold}
    {underline}
    }}'''

def InspectorHeaderStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `hoverColor`, `borderColor`, `borderRadius`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QWidget {{
    background-color: transparent;
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    text-align: left;
    border: none;
    border-radius: {kwargs.get('borderRadius', 0)};
    padding: 5px;
    padding-left: 15px;
    }}
    QPushButton {{
    background-color: {kwargs.get('color', tabSelectedColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    padding-left: 10px;
    padding-top: 5px;
    padding-right: 10px;
    padding-bottom: 5px;
    border: 2px solid {kwargs.get('borderColor', buttonBorderColor)};
    border-radius: 5px;
    margin-left: 1px;
    margin-bottom: 10px;
    }}
    QPushButton:hover {{
    background-color: {kwargs.get('hoverColor', tabHoverColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    padding-left: 10px;
    padding-top: 5px;
    padding-right: 10px;
    padding-bottom: 5px;
    border: 2px solid {kwargs.get('borderColor', buttonBorderColor)};
    border-radius: 5px;
    margin-left: 1px;
    margin-bottom: 10px;
    }}'''

def InspectorHeaderHousingStyle(**kwargs): 
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `borderColor`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QWidget {{
    background-color: transparent;
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    text-align: left;
    border: none;
    border-radius: 2px;
    padding: 5px;
    padding-left: 15px;
    margin-left: -3px;
    }}'''

def InspectorNameHousingStyle(**kwargs): 
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QLabel {{
    background-color: {kwargs.get('color', buttonColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    padding: 0px;
    margin: 0px;
    text-align: center;
    }}'''

def ListWidget(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QListWidget {{
    background-color: transparent;
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    border: none;
    }}
    QListWidget::item:selected {{
        background: transparent;
        color: inherit;
    }}'''

def ListView(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `hoverColor`, `fontColor`, `fontSize`, `fontFamily`, `spacing`'''
    return f'''
    QListView {{
    background-color: {kwargs.get('color')};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    border: none;
    }}
    QListView::item {{
    background-color: {kwargs.get('color')};
    padding-top: {kwargs.get('spacing', 0)}px;
    padding-bottom: {kwargs.get('spacing', 0)}px;
    }}
    QListView::item:hover {{
    background-color: {kwargs.get('hoverColor')};
    padding-top: {kwargs.get('spacing', 0)}px;
    padding-bottom: {kwargs.get('spacing', 0)}px;
    }}
    QListView::item:selected {{
    background-color: {kwargs.get('hoverColor')};
    padding-top: {kwargs.get('spacing', 0)}px;
    padding-bottom: {kwargs.get('spacing', 0)}px;
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    border: none;
    }}'''

def ProgressBarStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `borderColor`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QProgressBar {{
    background-color: {kwargs.get('color', buttonColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    text-align: center;
    border: 2px solid {kwargs.get('borderColor', 'black')};
    border-radius: {kwargs.get('borderRadius', 0)}px;
    }}'''

def ScrollBarStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `handleColor`, `backgroundColor`'''
    return f'''
    QScrollBar:vertical {{
    border: none;
    background: {kwargs.get('backgroundColor', buttonColor)};
    width: 15px;
    margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
    background: {kwargs.get('handleColor', tabSelectedColor)};
    min-height: 20px;
    border-radius: 2px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    subcontrol-origin: margin;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    }}
    QScrollBar:horizontal {{
    border: none;
    background: {kwargs.get('backgroundColor', buttonColor)};
    height: 15px;
    margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:horizontal {{
    background: {kwargs.get('handleColor', tabSelectedColor)};
    min-width: 20px;
    border-radius: 2px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    subcontrol-origin: margin;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
    }}'''

def MenuStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `hoverColor`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QMenu::item {{
    background-color: {kwargs.get('color', buttonSelectedColor)};
    padding-left: 10px;
    padding-top: 10px;
    padding-right: 30px;
    padding-bottom: 10px;
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    border: none;
    }}
    QMenu::item:selected {{
    background-color: {kwargs.get('hoverColor', buttonHoverColor)};
    padding-left: 10px;
    padding-top: 10px;
    padding-right: 30px;
    padding-bottom: 10px;
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    border: none;
    }}'''

def ListWidgetStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QListWidget {{
    background-color: transparent;
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    font-weight: bold;
    border: none;
    }}
    QListWidget::item:selected {{
        background: transparent;
        color: inherit;
    }}'''

def SliderStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `backgroundColor`, `handleColor`, `handleEdgeColor`, `fillColor`'''
    return f'''
    QSlider::groove:horizontal {{
    height: 10px;
    background: {kwargs.get('backgroundColor')};
    border-radius: 5px;
    margin: 0 0px;
    margin-left: -1px;
    margin-right: -1px;
    }}
    QSlider::handle:horizontal {{
    background: {kwargs.get('handleColor')};
    height: 18px;
    width: 18px;
    border-radius: 9px;
    margin-top: -4px;
    margin-bottom: -4px;
    margin-left: -1px;
    margin-right: -1px;
    }}
    QSlider::sub-page:horizontal {{
    background: {kwargs.get('fillColor')};
    margin-left: 0px;
    border-radius: 5px;
    }}
    QSlider::add-page:horizontal {{
    background: transparent;
    margin: 0 -2px;
    margin-right: 0px;
    border-radius: 5px;
    }}
    '''

def EditorControlsStyle(**kwargs): 
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `borderColor`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QWidget {{
    background-color: {kwargs.get('color', buttonColor)};
    color: {kwargs.get('fontColor', fontColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    text-align: left;
    border: 2px solid {kwargs.get('borderColor', buttonBorderColor)};
    border-radius: 4px;
    }}'''

def EditorStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    Editor {{
    color: {kwargs.get('color', buttonColor)};
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    text-align: center;
    }}'''

def PVStyle(**kwargs):
    '''Accepts kwargs which should be set to #ABCDEF color strings.\n
    `color`, `borderColor`, `borderThickness`, `hoverColor`, `fontColor`, `fontSize`, `fontFamily`'''
    return f'''
    QWidget {{
    background-color: {kwargs.get('color', 'blue')};
    color: {kwargs.get('fontColor', fontColor)}
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    border: none;
    }}
    QFrame#PV {{
    background-color: {kwargs.get('color', 'red')};
    color: {kwargs.get('fontColor', fontColor)}
    font-size: {kwargs.get('fontSize', fontSize)}px;
    font-family: {kwargs.get('fontFamily', fontFamily)};
    border-radius: 5px;
    border: {kwargs.get('borderThickness')}px solid {kwargs.get('borderColor', buttonBorderColor)};
    }}'''

def ApplyMainStyle(**kwargs):
    '''Accepts kwargs, a dict of settings for each widget type.\n
    kwarg keys should take the form `<widget type> = dict(fontSize = 12, ...)`'''
    return WidgetStyle(**kwargs.get('widget', dict())) + FrameStyle(**kwargs.get('frame', dict())) + ScrollBarStyle(**kwargs.get('scrollbar', dict())) + PushButtonStyle(**kwargs.get('pushbutton', dict())) + ToolButtonStyle(**kwargs.get('toolbutton', dict())) + ComboStyle(**kwargs.get('combo', dict())) + LineEditStyle(**kwargs.get('lineedit', dict())) + TabStyle(**kwargs.get('tab', dict())) + TabWidgetStyle(**kwargs.get('tabwidget', dict())) + LabelStyle(**kwargs.get('label', dict())) + ListWidgetStyle(**kwargs.get('listwidget', dict())) + ProgressBarStyle(**kwargs.get('progressbar', dict()))

def Light01():
    shared.lightModeOn = not shared.lightModeOn
    for p in shared.PVs:
        p.UpdateColors() # Apply a color update without toggling the selection state of the PV.
    for e in shared.expandables.values():
        e.UpdateColors() # Apply a color update to the expandable widgets in the inspector if a PV is currently selected.
        if e.widget is not None:
            e.widget.UpdateColors()
    for e in shared.editors:
        e.scene.setBackgroundBrush(QColor(229, 223, 204))
        if hasattr(e, 'popup'):
            e.popup.UpdateColors()
    shared.inspector.mainWindow.setStyleSheet(WidgetStyle(color = '#E5DFCC'))
    shared.inspector.mainWindowTitle.setStyleSheet(LabelStyle(fontColor = '#1e1e1e', fontSize = 16))
    shared.workspace.UpdateColors()
    return WidgetStyle(color = '#D8D3C0', fontColor = '#1C1C1C') + FrameStyle(color = '#E5DFCC', fontColor = '#1C1C1C') + ScrollBarStyle(handleColor = '#B5AB8D', backgroundColor = '#C9C3B1') + PushButtonStyle(color = '#D2C5A0', hoverColor = '#B5AB8D', padding = '0px', fontColor = '#1C1C1C') + PushButtonBorderlessStyle(color = '#D2C5A0', hoverColor = '#B5AB8D', fontColor = '#1e1e1e') + ToolButtonStyle(color = '#D7CDAB', fontColor = '#1C1C1C') + ComboStyle() + LineEditStyle(color = '#D2C5A0') + TabStyle(color = '#E5DFCC', hoverColor = '#B5AB8D', selectedColor = '#D2C5A0', fontColor = '#1C1C1C') + TabWidgetStyle(fontColor = '#1C1C1C') + EditorStyle() + LabelStyle(fontColor = '#1c1c1c') + ProgressBarStyle(color = '#E5DFCC', borderColor = '#D2C5A0', borderRadius = 5, fontColor = '#1e1e1e')

def Dark01():
    shared.lightModeOn = not shared.lightModeOn
    for p in shared.PVs.values():
        p['pv'].UpdateColors() # Apply a color update without toggling the selection state of the PV.
    for e in shared.expandables.values():
        e.UpdateColors() # Apply a color update to the expandable widgets in the inspector if a PV is currently selected.
        if e.widget is not None:
            e.widget.UpdateColors()
    for e in shared.editors:
        if hasattr(e, 'popup'):
            e.popup.UpdateColors()
    # shared.inspector.mainWindow.setStyleSheet(WidgetStyle(color = '#1a1a1a')) # controls color of the inspector.
    return WidgetStyle(color = '#1e1e1e', fontColor = '#C4C4C4') + FrameStyle(color = '#1a1a1a', borderColor = '#1a1a1a', fontColor = '#C4C4C4') + ScrollBarStyle(handleColor = '#2d2d2d', backgroundColor = '#363636') + PushButtonStyle(color = '#262626', hoverColor = '#3D3D3D', padding = '0px', fontColor = '#C4C4C4') + PushButtonBorderlessStyle(color = '#262626', hoverColor = '#3D3D3D', fontColor = '#c4c4c4') + ToolButtonStyle(color = '#09BC8A', fontColor = '#C4C4C4') + ComboStyle() + LineEditStyle(color = '#222222') + TabStyle(color = '#1a1a1a', hoverColor = '#B26A17', selectedColor = '#39393A', fontColor = '#C4C4C4') + TabWidgetStyle(color = '#1a1a1a', fontColor = '#C4C4C4') + EditorStyle() + LabelStyle(fontColor = '#C4C4C4') + ProgressBarStyle(color = '#262626', borderColor = '#3C4048', borderRadius = 5, fontColor = '#c4c4c4')

def socketStyle(radius, color = tabSelectedColor, alignment = 'left'):
    '''`alignment` is the side of the widget the socket sits on.'''
    align = f'''
    border-top-left-radius: {radius}px;
    border-top-right-radius: 0px;
    border-bottom-right-radius: 0px;
    border-bottom-left-radius: {radius}px;
    border-right: none;
    '''
    if alignment == 'right':
        align = f'''
        border-top-left-radius: 0px;
        border-top-right-radius: {radius}px;
        border-bottom-right-radius: {radius}px;
        border-bottom-left-radius: 0px;
        border-left: none;
        '''
    return f'''
    QFrame {{
    background-color: {color};
    border: 2px solid {color};
    {align}
    }}'''

def IndicatorStyle(radius, color = 'transparent', borderColor = None):
    '''`radius` is an int and `color`, `borderColor` are hex color strings (#ABCDEF).'''
    border = 'border: none;' if not borderColor else f'border: 1px solid {borderColor};'
    return f'''
    QFrame {{
    background-color: {color};
    border-radius: {radius}px;
    {border}
    }}'''

def AdjustLabelColor(label, color = 'transparent'):
    label.setStyleSheet(f'''
    QLabel {{
    background-color: {color};
    color: {fontColor};
    font-size: {fontSize};
    font-family: {fontFamily};
    padding: 0px;
    margin: 0px;
    text-align: center;
    }}''')

def AdjustButtonColor(button, state, color = buttonSelectedColor):
    if state == 'pressed':
        button.setStyleSheet(f'''
        QPushButton {{
        background-color: {color};
        color: {fontColor};
        font-size: {fontSize};
        font-family: {fontFamily};
        font-weight: bold;
        padding: 8px;
        border: 2px solid {buttonBorderColor};
        border-radius: 3px;
        }}''')
    elif state == 'released':
        button.setStyleSheet(PushButtonStyle())

def AdjustBorderlessButtonColor(button, state):
    if state == 'pressed':
        button.setStyleSheet(f'''
        QPushButton {{
        background-color: {buttonSelectedColor};
        color: {fontColor};
        font-size: {fontSize};
        font-family: {fontFamily};
        font-weight: bold;
        padding-left: 10px;
        padding-top: 5px;
        padding-right: 10px;
        padding-bottom: 5px;
        border: none;
        border-radius: 0px;
        }}''')
    elif state == 'released':
        button.setStyleSheet(PushButtonBorderlessStyle())

def AdjustToolButtonColor(button, state):
    if state == 'pressed':
        button.setStyleSheet(f'''
        QToolButton {{
        background-color: {buttonSelectedColor};
        color: {fontColor};
        font-size: {fontSize};
        font-family: {fontFamily};
        font-weight: bold;
        padding: 5px;
        }}
        QToolButton::menu-indicator {{
            image: none;
        }}''')
    elif state == 'released':
        button.setStyleSheet(ToolButtonStyle())