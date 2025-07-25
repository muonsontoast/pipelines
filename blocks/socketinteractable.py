from PySide6.QtWidgets import QFrame, QLabel, QGraphicsLineItem, QHBoxLayout
from PySide6.QtCore import Qt, QSize, QLineF, QEvent
from PySide6.QtGui import QPen, QColor, QCursor
from .. import style
from .. import shared

# Sockets have three types: M, F and MF
# M extend links
# F receive links
# MF extend AND receive links

class SocketInteractable(QFrame):
    def __init__(self, parent, diameter, type, alignment, **kwargs):
        '''`type` should be a string <M/F/MF>\n
        M = extend links\n
        F = receive links\n
        MF = extend and receive links\n
        `**kwargs` admits an `acceptableTypes` list of valid block types that may connect.'''
        super().__init__()
        self.parent = parent
        self.diameter = diameter
        self.type = type
        self.acceptableTypes = kwargs.get('acceptableTypes', list())
        self.entered = False
        self.setFixedSize(self.diameter, self.diameter)
        self.setStyleSheet(style.socketStyle(self.diameter / 2, alignment = alignment))
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

    def enterEvent(self, event):
        '''Another PV mouseMove event is in control until the mouse is released, this method will then be called upon release.'''
        if self.entered:
            return
        print('Entered the socket of', self.parent.parent.settings['name'])
        self.parent.parent.hoveringSocket = self.parent
        self.entered = True
        self.parent.parent.canDrag = False
        self.parent.parent.hovering = False
        if shared.PVLinkSource is not None and shared.PVLinkSource != self.parent.parent and self.type in ['F', 'MF']:
            if shared.PVLinkSource.__class__ not in self.acceptableTypes:
                return
            # some name filtering
            name = self.parent.name[:-1] # socket names are plural so remove the 's'
            if name not in ['BPM']:
                name = name.lower()
            shared.PVLinkSource.linkTarget = self.parent.parent
            if 'free' in shared.PVLinkSource.links.keys():
                shared.PVLinkSource.indicator.setStyleSheet(style.indicatorStyle(4, color = "#E0A159", borderColor = "#E7902D"))
                shared.PVLinkSource.links['free'].setLine(QLineF(shared.PVLinkSource.socketPos, self.parent.parent.GetSocketPos(name)))
                self.parent.parent.linksIn[shared.PVLinkSource.links['free']] = name
                shared.PVLinkSource.links[f'{self.parent.name}'] = shared.PVLinkSource.links.pop('free')
                # Show the link (reshows free link after hidden by the pv upon mouse release)
                shared.editors[0].scene.addItem(shared.PVLinkSource.links[f'{self.parent.name}'])
                if self.parent.parent.__class__ == shared.blockTypes['Orbit Response']:
                    if self.parent.name == 'Correctors':
                        self.parent.parent.correctors.append(shared.PVLinkSource)
                    else:
                        self.parent.parent.BPMs.append(shared.PVLinkSource)

                if not self.parent.parent.runningCircle.running:
                    print('Starting running circle')
                    self.parent.parent.runningCircle.Start()
                else:
                    print('Stopping running circle')
                    self.parent.parent.runningCircle.Stop()


    def leaveEvent(self, event):
        self.entered = False
        self.hoveringSocket = False
        self.parent.parent.canDrag = True
        if shared.PVLinkSource is not None and shared.PVLinkSource != self.parent.parent and self.type in ['F', 'MF']:
            shared.PVLinkSource.linkTarget = None