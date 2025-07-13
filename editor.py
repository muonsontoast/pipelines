from PySide6.QtWidgets import (
    QFrame, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QGraphicsProxyWidget, QGraphicsWidget,
    QWidget, QLabel, QGridLayout, QHBoxLayout, QGraphicsGridLayout, QVBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, Property, QPoint, QPointF, QSizeF, QRect
from PySide6.QtGui import QColor, QBrush, QTransform, QPen, QPainter, QRegion
from . import shared
from . import pv
from . import entity
from . import style
from . import editorpopup

# 2) Your styled widget
class MyStyledWidget(QWidget):
    def __init__(self):
        super().__init__()
        # Let the stylesheet draw the whole background…
        self.setAttribute(Qt.WA_StyledBackground, True)
        # …and make the canvas underneath actually transparent
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.setStyleSheet("""
            background-color: #2b2b2b;
            color: white;
            border: 2px solid #444;
            border-radius: 12px;
            font-weight: bold;
            padding: 10px;
        """)

        layout = QHBoxLayout(self)
        layout.addWidget(QLabel("Rounded, bold text, custom border—all intact!"))

class Editor(QGraphicsView):
    def __init__(self, window):
        super().__init__()
        self.parent = window
        self.settings = dict()
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.viewport().setCursor(Qt.ArrowCursor)
        self.setFrameStyle(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setSceneRect(0, 0, 3000, 3000)
        self.popup = editorpopup.Popup(self, 975, 125, 250, 450)
        # Test widget
        pvWidget = pv.PV(self, 'LOL :)')
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(pvWidget)
        proxy.setPos(1500, 1500)
        self.scene.addItem(proxy)

        pvWidget = pv.PV(self, 'Welp')
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(pvWidget)
        proxy.setPos(1500, 1650)
        self.scene.addItem(proxy)

        pvWidget = pv.PV(self, 'CI:XFER:VSTR:05-01:I')
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(pvWidget)
        proxy.setPos(1500, 1800)
        self.scene.addItem(proxy)
        self.centerOn(1400, 1400)

        self.startPos = None

    def mousePressEvent(self, event):
        self.startPos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if shared.selectedPV is not None:
            delta = event.pos() - self.startPos
            hovering = False
            for p in shared.PVs:
                if p.hovering:
                    hovering = True
                    break
            if not hovering and (delta.x() ** 2 + delta.y() ** 2) ** .5 < shared.cursorTolerance:
                shared.selectedPV.cursorMoved = False
                shared.selectedPV.ToggleStyling()
                shared.selectedPV.startPos = None
                shared.selectedPV = None
                entity.mainWindow.inspector.Push()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.angleDelta().y() != 0:
            return
        super().wheelEvent(event)

    def AssignSettings(self, **kwargs):
        for k, v in kwargs.items():
            self.settings[k] = v

    def GetSettings(self):
        return self.settings