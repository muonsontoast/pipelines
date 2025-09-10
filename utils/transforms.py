from PySide6.QtCore import QRectF
from .. import shared

def MapSocketRectToScene(widget):
    '''Nested widgets inside a proxy widget don\'t map correctly under `.mapToScene()`, so this method should be called instead.'''
    topLeft = widget.rect().topLeft()
    topLeftInSceneCoords = widget.parent.parent.proxy.mapToScene(widget.mapTo(widget.parent.parent, widget.mapTo(widget.parent, topLeft)))
    bottomRight = widget.rect().bottomRight()
    bottomRightInSceneCoords = widget.parent.parent.proxy.mapToScene(widget.mapTo(widget.parent.parent, widget.mapTo(widget.parent, bottomRight)))
    widget.rectInSceneCoords = QRectF(topLeftInSceneCoords, bottomRightInSceneCoords)
    return widget.rectInSceneCoords

def MapDraggableRectToScene(widget):
    topLeft = widget.rect().topLeft()
    topLeftInSceneCoords = widget.proxy.mapToScene(topLeft)
    bottomRight = widget.rect().bottomRight()
    bottomRightInSceneCoords = widget.proxy.mapToScene(bottomRight)
    widget.rectInSceneCoords = QRectF(topLeftInSceneCoords, bottomRightInSceneCoords)
    return widget.rectInSceneCoords

def MapViewportRectToScene():
    topLeft = shared.activeEditor.viewport().rect().topLeft()
    topLeftInSceneCoords = shared.activeEditor.mapToScene(topLeft)
    bottomRight = shared.activeEditor.viewport().rect().bottomRight()
    bottomRightInSceneCoords = shared.activeEditor.mapToScene(bottomRight)
    shared.activeEditor.rectInSceneCoords = QRectF(topLeftInSceneCoords, bottomRightInSceneCoords)
    return shared.activeEditor.rectInSceneCoords

def MultiSceneBoundingRect():
    selectedItems = shared.activeEditor.area.selectedItems
    if not selectedItems:
        return QRectF()
    
    rect = selectedItems[0].sceneBoundingRect()
    for item in selectedItems[1:]:
        rect = rect.united(item.sceneBoundingRect())
    return rect