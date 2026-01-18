from PySide6.QtWidgets import QFrame, QWidget, QLabel, QPushButton, QGraphicsProxyWidget, QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsLineItem, QSizePolicy, QSpacerItem, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import QPainter, QCursor, QPixmap
from .editormenu import EditorMenu
from .boxselect import BoxSelect
from ..blocks.pv import PV
from ..utils.entity import Entity
from ..utils.commands import DetailedView
from .. import shared
from .. import style

class Editor(Entity, QGraphicsView):
    def __init__(self, window, minScale = 3, maxScale = .15):
        '''Scale gets larger the more you zoom in, so `minScale` is max zoom in (> 1) and `maxScale` is max zoom out (< 1)'''
        super().__init__(name = 'Editor', type = 'Editor', zoom = 1)
        self.parent = window
        self.minScale = minScale
        self.maxScale = maxScale
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.canDrag = False
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setFrameStyle(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setSceneRect(0, 0, 10000, 10000)
        shared.editors.append(self)
        self.menu = EditorMenu(self)
        self.centerOn(5000, 5000)

        # grab handle for performing group movement of selected items
        self.grabHandle = QGraphicsProxyWidget()
        self.grabWidget = QLabel()
        pixmap = QPixmap(shared.cwd + '\\gfx\\drag.png')
        pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.grabWidget.setPixmap(pixmap)
        self.grabWidget.setStyleSheet('background: transparent; background-color: #c4c4c4;')
        self.grabHandle.setWidget(self.grabWidget)
        self.scene.addItem(self.grabHandle)
        self.grabHandle.hide() # hide by default

        self.startPos = None
        self.currentPos = None
        self.globalStartPos = None
        self.mouseButtonPressed = None # to be deprecated
        self.keysPressed:list[Qt.Key] = []
        self.area:BoxSelect = BoxSelect()
        self.areaEnabled:bool = False

        self.coordsTitle = QLabel()
        self.zoomTitle = QLabel()

        self.positionInSceneCoords = self.mapToScene(self.viewport().rect().center())
        self.coordsTitle.setText(f'Editor center: ({self.positionInSceneCoords.x():.0f}, {self.positionInSceneCoords.y():.0f})')
        self.zoomTitle.setText(f'Zoom: {self.transform().m11() * 100:.0f}%')

        # add a groups overlay widget to the graphics view
        self.setLayout(QHBoxLayout())
        self.groupsWidget = QWidget()
        self.layout().addWidget(self.groupsWidget, alignment = Qt.AlignRight | Qt.AlignTop)
        self.groupsWidget.setFixedSize(65, 35)
        self.groupsWidget.setLayout(QVBoxLayout())
        self.groupsWidget.setContentsMargins(0, 0, 0, 0)
        self.groupsWidget.layout().setContentsMargins(0, 0, 0, 0)
        header = QWidget()
        header.setLayout(QVBoxLayout())
        header.setContentsMargins(0, 0, 0, 0)
        label = QLabel('Groups')
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(style.LabelStyle(padding = 0))
        header.layout().addWidget(label)
        self.groupsWidget.layout().addWidget(header)
        self.groupsWidget.setStyleSheet(style.WidgetStyle(color = 'none'))
        header.setStyleSheet(style.WidgetStyle(color = '#2e2e2e', fontColor = '#c4c4c4', borderRadius = 4))

    # this draw override prevents widget artefacting when dragging blocks around a scene
    def drawBackground(self, painter, rect):
        pass

    def SetCacheMode(self, mode = 'Device', widgetToIgnore = None):
        '''Restores the image cache of blocks in the scene.\n
        `item` should be one of <Device/None>\n
        `widgetToIgnore` is a widget that should not be cached (such as one being dragged aroudn the scene).'''
        if mode == 'Device':
            for item in self.scene.items():
                if not isinstance(item, QGraphicsLineItem):
                    if widgetToIgnore == item: # don't cache widgets which are being moved.
                        item.setCacheMode(QGraphicsItem.NoCache)
                        item.update()
                        continue
                    item.setCacheMode(QGraphicsItem.DeviceCoordinateCache) # -- may need to re-enable this!
        else:
            for item in self.scene.items():
                item.setCacheMode(QGraphicsItem.NoCache)

    def GetEntityWidgetAtClick(self, widget):
        current = widget
        proxy = None
        while current and not proxy:
            proxy = current.graphicsProxyWidget()
            try:
                current = current.parent()
            except: break
        return current

    def mousePressEvent(self, event):
        '''Another PV may already be selected so handle this here.'''
        if event is None:
            self.startPos = QPoint(0, 0)
        else:
            self.startPos = self.mapToScene(event.position().toPoint())
        self.globalStartPos = event.position()
        if not self.menu.hidden and shared.PVs[self.menu.ID]['rect'].contains(self.startPos):
            return super().mousePressEvent(event)
        
        self.canDrag = True

        # fetch all selected proxies
        intersectingWidgets = [
            item for item in self.scene.items(QRectF(self.startPos.x(), self.startPos.y(), 1, 1), Qt.IntersectsItemBoundingRect)
            if isinstance(item, QGraphicsProxyWidget) and item != self.area
        ]
        # check whether shift alone is being pressed
        if self.keysPressed == [Qt.Key_Shift]:
            self.area.setPos(self.startPos)
            self.area.resize(0, 0)
            self.scene.addItem(self.area)
            self.areaEnabled = True
        self.menu.Hide()
        if not intersectingWidgets:
            self.SetCacheMode()
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.canDrag = False
            self.SetCacheMode('None')
            self.setDragMode(QGraphicsView.NoDrag)
        self.mouseButtonPressed = event.button()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.currentPos = self.mapToScene(event.position().toPoint())
        if self.mouseButtonPressed == Qt.LeftButton:
            self.positionInSceneCoords = self.mapToScene(self.viewport().rect().center())
            self.coordsTitle.setText(f'Editor centre: ({self.positionInSceneCoords.x():.0f}, {self.positionInSceneCoords.y():.0f})')
            if self.areaEnabled:
                # update box select size and position
                ds = self.currentPos - self.startPos
                self.area.setPos(self.startPos.x() + min(ds.x(), 0), self.startPos.y() + min(ds.y(), 0))
                self.area.resize(abs(ds.x()), abs(ds.y()))

                # fetch all selected proxies
                intersectingWidgets = [
                    item for item in self.scene.items(self.area.sceneBoundingRect(), Qt.IntersectsItemBoundingRect)
                    if isinstance(item, QGraphicsProxyWidget) and item != self.area
                ]

                # remove newly deselected items
                for item in self.area.selectedItems:
                    if item not in intersectingWidgets:
                        item.widget().ToggleStyling(active = False)
                        self.area.selectedItems.remove(item)
                
                # add newly selected items
                for item in intersectingWidgets:
                    if item not in self.area.selectedItems:
                        item.widget().ToggleStyling(active = True)
                        self.area.selectedItems.append(item)

                return event.ignore()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        mousePos = self.mapToScene(event.position().toPoint())
        # ds = mousePos - self.startPos
        globalMousePos = event.position()
        ds = globalMousePos - self.globalStartPos
        # fetch all selected proxies
        intersectingWidgets = [
            item for item in self.scene.items(QRectF(mousePos.x(), mousePos.y(), 1, 1), Qt.IntersectsItemBoundingRect)
            if isinstance(item, QGraphicsProxyWidget) and item != self.area
        ]
        # clean up area selection
        if self.areaEnabled:
            self.scene.removeItem(self.area)
            self.areaEnabled = False
        if self.mouseButtonPressed == Qt.RightButton:
            if not self.menu.ID in shared.PVs.keys() or not shared.PVs[self.menu.ID]['rect'].contains(mousePos):
                self.menu.Show(mousePos - shared.editorMenuOffset)
            event.accept()
            return
        elif not self.canDrag:
            if not self.menu.hidden and shared.PVs[self.menu.ID]['rect'].contains(mousePos):
                return super().mouseReleaseEvent(event)
            if ds.x() ** 2 + ds.y() ** 2 < shared.cursorTolerance ** 2:
                item = intersectingWidgets[0]
                mousePosInProxyCoords = item.mapFromScene(mousePos)
                proxyChildUnderCursor = item.widget().childAt(mousePosInProxyCoords.toPoint())
                # close kernel menu if it is open anywhere
                draggable = getattr(proxyChildUnderCursor, 'draggable', None)
                if shared.kernelMenu is not None:
                    if draggable is None:
                        shared.kernelMenu.draggable.kernelMenuIsOpen = False
                        shared.kernelMenu.Hide()
                        shared.kernelMenu = None
                # allow interactions with buttons / menus without affecting selections
                if type(proxyChildUnderCursor) not in [QPushButton]:
                    # check for shift click
                    if self.keysPressed == [Qt.Key_Shift]:
                        item.widget().ToggleStyling()
                        # remove if inactive after toggle, else add
                        if item.widget().active:
                            self.area.selectedItems.append(item)
                            if type(item.widget().type) in ['BPM', 'Corrector', 'PV']:
                                shared.inspector.Push(item.widget())
                        else:
                            if item in self.area.selectedItems:
                                self.area.selectedItems.remove(item)
                                shared.inspector.Push()
                        self.SetCacheMode('None')
                        return
                    else:
                        for _item in self.area.selectedItems:
                            if _item != item:
                                _item.widget().ToggleStyling(active = False)
                        self.area.selectedItems = [item]
                        if shared.editorSelectMode:
                            widget = self.GetEntityWidgetAtClick(proxyChildUnderCursor)
                            if not isinstance(widget, PV):
                                shared.editorSelectMode = False
                                shared.activeEditor.setStyleSheet(style.WidgetStyle(color = "#1a1a1a"))
                                for ID in shared.PVIDs:
                                    shared.entities[ID].BaseStyling()
                            else:
                                return event.accept()
        else:
            if ds.x() ** 2 + ds.y() ** 2 < shared.cursorTolerance ** 2: # cursor has been moved.
                if shared.kernelMenu is not None:
                    shared.kernelMenu.draggable.CloseMenu(shared.kernelContext)
                for item in self.area.selectedItems:
                    item.widget().ToggleStyling(active = False)
                if shared.editorSelectMode:
                    shared.editorSelectMode = False
                    shared.activeEditor.setStyleSheet(style.WidgetStyle(color = "#1a1a1a"))
                    for ID in shared.PVIDs:
                        shared.entities[ID].BaseStyling()
                self.area.selectedItems = []
                shared.inspector.Push()

        self.SetCacheMode('None')
        super().mouseReleaseEvent(event) # the event needs to propagate beyond the editor to allow drag functionality.

    def MoveSelectionIcons(self, mousePos):
        '''Places handles adjacent to selections for group actions.'''
        for item in self.area.selectedItems:
            item.widget().setPos()

    def wheelEvent(self, event):
        # Check if cursor is over quick menu
        if not self.menu.hidden and shared.PVs[self.menu.ID]['rect'].contains(self.currentPos):
            shared.app.sendEvent(self.menu, event)
            event.accept()
            return
        else:
            cursorPos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
            for p in shared.PVs.values():
                if p['pv'].type == 'Save':
                    if p['rect'].contains(cursorPos):
                        shared.app.sendEvent(p['pv'], event)
                        event.accept()
                        return
        angle = event.angleDelta().y()
        zoomFactor = 1 + angle / 2000
        # get current scale
        currentScale = self.transform().m11()
        if (currentScale * zoomFactor > self.minScale) or (currentScale * zoomFactor < self.maxScale):
            event.accept()
            return
        
        self.scale(zoomFactor, zoomFactor)
        zoom = self.transform().m11()
        self.zoomTitle.setText(f'Zoom: {zoom * 100:.0f}%')
        self.settings['zoom'] = zoom
        self.SetCacheMode('None')
        event.accept()

    def keyPressEvent(self, event):
        if not event.key() in self.keysPressed:
            self.keysPressed.append(event.key())
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_Return):
            if not self.menu.hidden:
                shared.app.sendEvent(self.menu, event)
                event.accept()
                return
            else:
                cursorPos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
                for p in shared.PVs.values():
                    if p['pv'].type == 'Save':
                        if p['rect'].contains(cursorPos):
                            shared.app.sendEvent(p['pv'], event)
                            return event.accept()
        elif self.keysPressed == [Qt.Key_Alt]:
            DetailedView()

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        if Qt.Key_Alt in self.keysPressed:
            DetailedView(False)
        if event.key() in self.keysPressed:
            self.keysPressed.remove(event.key())
        return super().keyReleaseEvent(event)