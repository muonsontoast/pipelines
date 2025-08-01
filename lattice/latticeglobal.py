from PySide6.QtWidgets import (
    QWidget, QFrame, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem, QVBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from ..utils.entity import Entity
from .. import shared

class LatticeGlobal(Entity, QWidget):
    # Lattice should fit into size 1250 width x 50 height
    # (0, 0) is at the top left of the graphics view
    def __init__(self, parent):
        super().__init__(name = 'Global Lattice', type = 'Global Lattice', sceneWidth = 1200, sceneHeight = 145)
        self.parent = parent
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        # Define width and height of scene
        self.sceneWidth = 1200
        self.sceneHeight = 145
        self.halfHeight = self.sceneHeight / 2
        self.verticalCenter = self.sceneHeight / 2 + 20
        self.elementThickness = .0075 * self.sceneWidth
        # Create a scene
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(0, 0, self.sceneWidth, self.sceneHeight) # in scene coordinates
        self.view = QGraphicsView(self.scene)
        # Beam axis
        axis = QGraphicsLineItem(0, self.verticalCenter, 1250, self.verticalCenter)
        axis.setPen(QPen(QColor('#3e3e3e'), 3))
        self.scene.addItem(axis)
        # Add some elements
        self.labels = []
        for _, e in shared.elements.iterrows():
            if e.Type == 'Quadrupole':
                self.AddQuadrupole(e)
            elif e.Type == 'Dipole':
                self.AddDipole(e)
            elif e.Type == 'Corrector':
                self.AddCorrector(e)
            elif e.Type == 'Marker' and 'BPM' in e.Name:
                self.AddBPM(e)
        # Add legend
        self.AddLegend()
        # Configure view
        self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.layout().addWidget(self.view)

    def AddDipole(self, element):
        '''Accepts `element`, an element from a .mat lattice file.'''
        # iloc[2] = s position of an element
        if 'Dipole' not in self.labels:
            self.labels.append('Dipole')
        normalisedS = element.iloc[2] / shared.elements.iloc[-1].iloc[2] * self.sceneWidth
        dipole = QGraphicsRectItem(normalisedS, self.verticalCenter - self.halfHeight / 2, self.elementThickness, self.halfHeight)
        dipole.setPen(Qt.NoPen)
        dipole.setBrush(QBrush("#f4bf00"))
        self.scene.addItem(dipole)
        shared.app.processEvents()

    def AddQuadrupole(self, element):
        # Convention is that negative K is a focusing quadrupole
        normalisedS = element.iloc[2] / shared.elements.iloc[-1].iloc[2] * self.sceneWidth
        focusing = shared.lattice[element.Index].K < 0
        if focusing:
            if 'Quadrupole Focusing' not in self.labels:
                self.labels.append('Quadrupole Focusing')
            quadrupole = QGraphicsRectItem(normalisedS, self.verticalCenter - self.halfHeight / 2, self.elementThickness, self.halfHeight / 2)
        else:
            if 'Quadrupole Defocusing' not in self.labels:
                self.labels.append('Quadrupole Defocusing') 
            quadrupole = QGraphicsRectItem(normalisedS, self.verticalCenter, self.elementThickness, self.halfHeight / 2)
        quadrupole.setZValue(-1)
        quadrupole.setPen(Qt.NoPen)
        quadrupole.setBrush(QBrush("#0066EB"))
        self.scene.addItem(quadrupole)
        shared.app.processEvents()

    def AddCorrector(self, element):
        if 'Corrector' not in self.labels:
            self.labels.append('Corrector')
        normalisedS = element.iloc[2] / shared.elements.iloc[-1].iloc[2] * self.sceneWidth
        corrector = QGraphicsRectItem(normalisedS, self.verticalCenter - 10, .25 * self.elementThickness, 20)
        corrector.setPen(Qt.NoPen)
        corrector.setBrush(QBrush("#E07700"))
        self.scene.addItem(corrector)
        shared.app.processEvents()

    def AddBPM(self, element):
        if 'BPM' not in self.labels:
            self.labels.append('BPM')
        normalisedS = element.iloc[2] / shared.elements.iloc[-1].iloc[2] * self.sceneWidth
        BPM = QGraphicsRectItem(normalisedS, self.verticalCenter - 5, .25 * self.elementThickness, 10)
        BPM.setPen(Qt.NoPen)
        BPM.setBrush(QBrush('#3e3e3e'))
        self.scene.addItem(BPM)
        shared.app.processEvents()

    def AddLegend(self):
        textWidths = {
            'Dipole': .1 * self.sceneWidth,
            'Quadrupole Focusing': .145 * self.sceneWidth,
            'Quadrupole Defocusing': .155 * self.sceneWidth,
            'BPM': .05 * self.sceneWidth,
            'Corrector': .085 * self.sceneWidth,
        }
        labelWidth = .025 * self.sceneWidth
        labelHeight = .175 * self.sceneHeight
        font = QFont("Consolas", 10)
        cumulativeWidth = 0
        fullWidth = 0
        for _, label in enumerate(self.labels):
            fullWidth += textWidths[label] + labelWidth
        legendStartPos = 625 - fullWidth / 2
        for _, label in enumerate(self.labels):
            x = legendStartPos + cumulativeWidth
            y = self.verticalCenter - .925 * self.halfHeight
            axis = QGraphicsLineItem(x, y, x + labelWidth, y)
            axis.setPen(QPen(QColor('#3e3e3e'), 3))
            self.scene.addItem(axis)
            if label == 'Dipole':
                dipole = QGraphicsRectItem(x + .35 * labelWidth, y - .5 * labelHeight, .3 * labelWidth, labelHeight)
                dipole.setPen(Qt.NoPen)
                dipole.setBrush(QBrush("#f4bf00"))
                self.scene.addItem(dipole)
            elif label == 'Quadrupole Focusing':
                quadrupole = QGraphicsRectItem(x + .35 * labelWidth, y - .5 * labelHeight, .3 * labelWidth, .5 * labelHeight)
                quadrupole.setZValue(-1)
                quadrupole.setPen(Qt.NoPen)
                quadrupole.setBrush(QBrush("#0066EB"))
                self.scene.addItem(quadrupole)
            elif label == 'Quadrupole Defocusing':
                quadrupole = QGraphicsRectItem(x + .35 * labelWidth, y, .3 * labelWidth, .5 * labelHeight)
                quadrupole.setZValue(-1)
                quadrupole.setPen(Qt.NoPen)
                quadrupole.setBrush(QBrush("#0066EB"))
                self.scene.addItem(quadrupole)
            elif label == 'Corrector':
                corrector = QGraphicsRectItem(x + .35 * labelWidth, y - .3 * labelHeight, .3 * labelWidth, .6 * labelHeight)
                corrector.setPen(Qt.NoPen)
                corrector.setBrush(QBrush("#E07700"))
                self.scene.addItem(corrector)
            elif label == 'BPM':
                BPM = QGraphicsRectItem(x + .35 * labelWidth, y - .2 * labelHeight, .3 * labelWidth, .4 * labelHeight)
                BPM.setPen(Qt.NoPen)
                BPM.setBrush(QBrush('#3e3e3e'))
                self.scene.addItem(BPM)
            text = QGraphicsTextItem(label)
            text.setDefaultTextColor('#c4c4c4')
            text.setFont(font)
            text.setPos(x + labelWidth + 10, y - 12)
            self.scene.addItem(text)
            cumulativeWidth += labelWidth + textWidths[label]