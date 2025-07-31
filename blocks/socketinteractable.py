from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, QLineF, QRectF
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
        self.rectInSceneCoords = None
        self.setFixedSize(self.diameter, self.diameter)
        self.setStyleSheet(style.socketStyle(self.diameter / 2, alignment = alignment))
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

    def enterEvent(self, event):
        '''Another PV mouseMove event is in control until the mouse is released, this method will then be called upon release.'''
        print(f'Hovering {self.parent.name}Socket')
        self.MapRectToScene()
        if shared.mousePosUponRelease is not None:
            if not self.rectInSceneCoords.contains(shared.mousePosUponRelease):
                return
        if self.entered:
            return
        self.parent.parent.hoveringSocket = self.parent
        self.entered = True
        self.parent.parent.canDrag = False
        self.parent.parent.hovering = False
        if shared.PVLinkSource is not None and shared.PVLinkSource != self.parent.parent and self.type in ['F', 'MF']:
            if shared.PVLinkSource.blockType not in self.acceptableTypes:
                shared.workspace.assistant.PushMessage(f'{shared.PVLinkSource.blockType} is not a valid input of {self.parent.name} socket. Acceptable types are: {', '.join(self.acceptableTypes)}.', 'Error')
                return
            if 'free' in shared.PVLinkSource.linksOut.keys():
                pushMessage = True
                if hasattr(shared.PVLinkSource, 'indicator'):
                    shared.PVLinkSource.indicator.setStyleSheet(style.indicatorStyle(4, color = "#E0A159", borderColor = "#E7902D"))
                shared.PVLinkSource.linksOut['free']['link'].setLine(QLineF(shared.PVLinkSource.GetSocketPos('output'), self.parent.parent.GetSocketPos(self.parent.name)))
                if shared.PVLinkSource.ID in self.parent.parent.linksIn.keys():
                    # redraw canvas with new data if re-linked.
                    shared.workspace.assistant.PushMessage(f'Link between {shared.PVLinkSource.name} and {self.parent.parent.name} already exists.', 'Warning')
                    pushMessage = False
                    shared.activeEditor.scene.removeItem(self.parent.parent.linksIn[shared.PVLinkSource.ID]['link'])
                self.parent.parent.linksIn[shared.PVLinkSource.ID] = dict(link = shared.PVLinkSource.linksOut['free']['link'], socket = self.parent.name)
                shared.PVLinkSource.linksOut[self.parent.parent.ID] = shared.PVLinkSource.linksOut.pop('free')
                shared.activeEditor.scene.addItem(self.parent.parent.linksIn[shared.PVLinkSource.ID]['link'])
                if self.parent.parent.blockType == 'Orbit Response':
                    if self.parent.name == 'corrector':
                        self.parent.parent.correctors[shared.PVLinkSource.ID] = shared.PVLinkSource
                    else:
                        self.parent.parent.BPMs[shared.PVLinkSource.ID] = shared.PVLinkSource
                elif self.parent.parent.blockType == 'View':
                    print('Block connected to a View block')
                    if shared.PVLinkSource.blockType == 'Orbit Response':
                        self.parent.parent.title.setText('View (Connected)')
                        self.parent.parent.PVIn = shared.PVLinkSource
                        self.parent.parent.DrawCanvas(stream = 'corrector')
                if pushMessage:
                    shared.workspace.assistant.PushMessage(f'Link created between {shared.PVLinkSource.name} and {self.parent.parent.name}.')
                shared.PVLinkSource = None

    def leaveEvent(self, event):
        self.entered = False
        self.hoveringSocket = False
        self.parent.parent.canDrag = True
        # if shared.PVLinkSource is not None and shared.PVLinkSource != self.parent.parent and self.type in ['F', 'MF']:
        #     shared.PVLinkSource.linkTarget = None

    def MapRectToScene(self):
        '''Nested widgets inside a proxy widget don\'t map correctly under `.mapToScene()`, so this method should be called instead.'''
        topLeft = self.rect().topLeft()
        topLeftInSceneCoords = self.parent.parent.proxy.mapToScene(self.mapTo(self.parent.parent, self.mapTo(self.parent, topLeft)))
        bottomRight = self.rect().bottomRight()
        bottomRightInSceneCoords = self.parent.parent.proxy.mapToScene(self.mapTo(self.parent.parent, self.mapTo(self.parent, bottomRight)))
        self.rectInSceneCoords = QRectF(topLeftInSceneCoords, bottomRightInSceneCoords)
        return self.rectInSceneCoords