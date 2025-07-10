from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import QSize
from . import style
from . import shared

class Expandable(QWidget):
    def __init__(self, listWidget, item, name):
        '''`list` the ListWidget containing the expandable widget.\n
        `item` is the ListWidgetItem this expandable is attached to.\n
        Accepts a list of kwarg widgets to display in the expandable content region.'''
        super().__init__()
        self.setFixedWidth(listWidget.viewport().width() - 5)
        self.parent = item
        self.setLayout(QVBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        # A dict of content widgets
        self.contentWidgets = dict()
        # Bool to keep track of whether to display the content.
        self.showingContent = False
        self.width = self.width()
        self.headerHeight = 40
        self.widgetsDrawn = False
        # Header button
        self.name = f'Control PV {name[9:]}' if name[:9] == 'controlPV' else name
        nameHousing = QWidget()
        nameHousing.setStyleSheet(style.inspectorHeaderHousingStyle)
        nameHousing.setLayout(QHBoxLayout())
        nameHousing.setContentsMargins(0, 0, 0, 0)
        self.header = QPushButton(f'\u25BA    {self.name}')
        self.header.setFixedSize(200, self.headerHeight)
        self.header.setCheckable(True)
        self.header.setStyleSheet(style.inspectorHeaderStyle)
        self.header.clicked.connect(self.ToggleContent)
        nameHousing.setFixedHeight(self.headerHeight)
        nameHousing.layout().addWidget(self.header)
        nameHousing.layout().addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.layout().addWidget(nameHousing)
        # Expandable area
        self.content = QListWidget()
        self.content.setStyleSheet(style.inspectorSectionStyle)
        self.content.setVisible(False)
        self.layout().addWidget(self.content)
        self.parent.setSizeHint(QSize(self.width, self.headerHeight + 10))

    def ToggleContent(self):
        shared.app.processEvents()
        # A new dict of housed widgets - saved the first time this expandable is opened.
        updatedWidgets = dict()
        shouldUpdateWidgets = False
        expandedHeight = 0
        if not self.showingContent:
            self.header.setText(f'\u25BC    {self.name}')
            for k, v in self.contentWidgets.items():
                # Is this the first time drawing widgets for this expandable?
                if not self.widgetsDrawn:
                    item = QListWidgetItem()
                    widget = QWidget()
                    widget.setContentsMargins(10, 0, 0, 0)
                    widget.setLayout(QHBoxLayout())
                    widget.layout().addWidget(v)
                    item.setSizeHint(widget.layout().sizeHint())
                    self.content.addItem(item)
                    self.content.setItemWidget(item, widget)
                    updatedWidgets[k] = widget
                    shouldUpdateWidgets = True
                else:
                    widget = self.contentWidgets[k]
                expandedHeight += widget.height()
            self.widgetsDrawn = True
            self.content.setVisible(True)
        else:
            self.header.setText(f'\u25BA    {self.name}')
            self.content.setVisible(False)
        
        self.content.setFixedHeight(expandedHeight)
        self.showingContent = not self.showingContent
        self.parent.setSizeHint(QSize(self.width, self.headerHeight + expandedHeight + 10))

        if shouldUpdateWidgets:
            self.contentWidgets = updatedWidgets

    # def sizeHint(self):
    #     return self.header.sizeHint() + self.content.sizeHint()

    # def sizeHint(self):
    #     # h = self.header.sizeHint().height()
    #     # if self.content.isVisible():
    #     #     h += self.content.height()
    #     # else:
    #     #     print('content not visible')
    #     # print('Final size hint is', self.header.sizeHint().width(), ',', h)
    #     # print('------')
    #     # return QSize(self.header.sizeHint().width(), h)
    #     return QSize(self.header.width(), self.header.height() + self.content.sizeHint().height())

    # def ToggleExpandableArea(self):
    #     print('content visibility', self.content.isVisible())
    #     # self.content.setVisible(True)
    #     # QApplication.processEvents()
    #     # time.sleep(2)
    #     print('is the content now visible?', self.content.isVisible())
    #     print('****************')
    #     # if hasattr(self, 'item'):
    #     #     self.item.setSizeHint(self.sizeHint())