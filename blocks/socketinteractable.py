from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, QLineF, QRectF
from copy import deepcopy
from .. import style
from .. import shared

# Sockets have three types: M, F and MF
# M extend links
# F receive links
# MF extend AND receive links

# List of socket names that aren't pluralised
socketNameBlacklist = ['Data']

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
        self.rectInSceneCoords = None
        self.setFixedSize(self.diameter, self.diameter)
        self.setStyleSheet(style.socketStyle(self.diameter / 2, alignment = alignment))
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

    def enterEvent(self, event):
        '''Another PV mouseMove event is in control until the mouse is released, this method will then be called upon release.'''
        print('Hovering', self.parent.name)
        self.MapRectToScene()
        if shared.mousePosUponRelease is not None:
            if not self.rectInSceneCoords.contains(shared.mousePosUponRelease):
                return
        if self.entered:
            print('b')
            return
        self.parent.parent.hoveringSocket = self.parent
        self.entered = True
        self.parent.parent.canDrag = False
        self.parent.parent.hovering = False
        if shared.PVLinkSource is not None and shared.PVLinkSource != self.parent.parent and self.type in ['F', 'MF']:
            print('e')
            if shared.PVLinkSource.__class__ not in self.acceptableTypes:
                print('c')
                return
            print('g')
            # some name filtering
            name = self.parent.name
            shared.PVLinkSource.linkTarget = self.parent.parent
            print('h')
            if 'free' in shared.PVLinkSource.linksOut.keys():
                print('l')
                if hasattr(shared.PVLinkSource, 'indicator'):
                    shared.PVLinkSource.indicator.setStyleSheet(style.indicatorStyle(4, color = "#E0A159", borderColor = "#E7902D"))
                print('m')
                print('output pos', shared.PVLinkSource.GetSocketPos('output'))
                print('data pos', self.parent.parent.GetSocketPos(name))
                shared.PVLinkSource.linksOut['free'].setLine(QLineF(shared.PVLinkSource.GetSocketPos('output'), self.parent.parent.GetSocketPos(name)))
                self.parent.parent.linksIn[shared.PVLinkSource.linksOut['free']] = name
                shared.PVLinkSource.linksOut[f'{self.parent.name}'] = shared.PVLinkSource.linksOut.pop('free')
                # Show the link (reshows free link after hidden by the pv upon mouse release)
                shared.editors[0].scene.addItem(shared.PVLinkSource.linksOut[f'{self.parent.name}'])
                blockType = self.parent.parent.__class__
                if blockType == shared.blockTypes['Orbit Response']:
                    if self.parent.name == 'corrector':
                        self.parent.parent.correctors.append(shared.PVLinkSource)
                    else:
                        self.parent.parent.BPMs.append(shared.PVLinkSource)
                elif blockType == shared.blockTypes['View']:
                    self.parent.parent.data = deepcopy(shared.PVLinkSource.data)
                shared.PVLinkSource = None
        print('d')

    def leaveEvent(self, event):
        self.entered = False
        self.hoveringSocket = False
        self.parent.parent.canDrag = True
        if shared.PVLinkSource is not None and shared.PVLinkSource != self.parent.parent and self.type in ['F', 'MF']:
            shared.PVLinkSource.linkTarget = None

    def MapRectToScene(self):
        '''Nested widgets inside a proxy widget don\'t map correctly under `.mapToScene()`, so this method should be called instead.'''
        topLeft = self.rect().topLeft()
        topLeftInSceneCoords = self.parent.parent.proxy.mapToScene(self.mapTo(self.parent.parent, self.mapTo(self.parent, topLeft)))
        bottomRight = self.rect().bottomRight()
        bottomRightInSceneCoords = self.parent.parent.proxy.mapToScene(self.mapTo(self.parent.parent, self.mapTo(self.parent, bottomRight)))
        self.rectInSceneCoords = QRectF(topLeftInSceneCoords, bottomRightInSceneCoords)
        return self.rectInSceneCoords