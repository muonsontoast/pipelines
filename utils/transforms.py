from PySide6.QtCore import QRectF

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