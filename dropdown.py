from PySide6.QtWidgets import QPushButton, QMenu
from PySide6.QtGui import QAction

class FilterButton(QPushButton):
    def __init__(self, label = "Filters", parent = None):
        super().__init__(label, parent)
        self.SetCheckable(False)
        self.SetPopupMode(QPushButton.InstantPopup)
        self.SetMenu(self.CreateMenu())

    def SetPopupMode(self, mode):
        self.setPopupMode(mode)

    def SetMenu(self, menu):
        self.setMenu(menu)

    def SetCheckable(self, checkable):
        self.setCheckable(checkable)

    def CreateMenu(self):
        menu = QMenu(self)
        self.actions = []

        for label in ["Apples", "Bananas", "Cherries"]:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(False)
            action.toggled.connect(lambda checked, name=label: print(f"{name}: {checked}"))
            menu.addAction(action)
            self.actions.append(action)

        return menu

    def AddFilterItem(self, label, checked = False):
        action = QAction(label, self)
        action.setCheckable(True)
        action.setChecked(checked)
        action.toggled.connect(lambda state, name=label: print(f"{name}: {state}"))
        self.menu().addAction(action)
        self.actions.append(action)


    def CheckedItems(self):
        return [action.text() for action in self.actions if action.isChecked()]