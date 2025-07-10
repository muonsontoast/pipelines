from PySide6.QtWidgets import QApplication
from itertools import product
from copy import deepcopy
import numpy as np
from .timer import Timer
from .simulator import Simulator

class Scanner:
    '''Performs grid scans.'''
    def __init__(self, window, stepDict):
        super().__init__()
        self.parent = window
        self.dataDict = dict(domains = dict(), data = np.zeros(shape = tuple(stepDict.values())), steps = 0)
        self.numSteps = 1
        for k, v in stepDict.items():
            controlSlider = self.parent.parent.parent.settingsDict['controlSliders'][k]
            self.dataDict['domains'][k] = np.linspace(controlSlider['sliderRange'][0], controlSlider['sliderRange'][1], v)
            self.numSteps *= v
        self.steps = 0
        self.data = dict()
        self.pauseScan = False
        self.stopScan = False
        self.working = False
        self.simulator = Simulator(self, self.parent.parent.parent.lattice)

    def AttemptToScan(self):
        # Check a monitor has been linked to this control panel
        if self.parent.linkedMonitor is None:
            self.parent.DisplayFailDialog('This control panel has not been linked to a monitor!', 'Missing Monitor!')
            return
        # Check control PVs have been selected
        if len(self.parent.linkedMonitor.controlPVNames) == 0:
            self.parent.DisplayFailDialog('No control PVs selected for the scan.', 'Missing Control PVs!')
            return
        # Check objective PVs have been selected
        if len(self.parent.linkedMonitor.objectivePVNames) == 0:
            if not self.parent.DisplayWarningDialog('No objective PVs selected for the scan. Are you sure you want to continue?', 'Missing Objective PVs!'):
                return
        # Check PVs are linked to lattice elements
        for pv in self.parent.linkedMonitor.controlPVNames:
            if 'elementName' not in self.parent.parent.parent.settingsDict['controlSliders'][pv].keys():
                self.parent.DisplayFailDialog(f'{pv} has not been linked to an element in the lattice!', 'Control PVs Missing Links!')
                return
        for pv in self.parent.linkedMonitor.objectivePVNames:
            if 'elementName' not in self.parent.parent.parent.settingsDict['objectiveSliders'][pv].keys():
                self.parent.DisplayFailDialog(f'{pv} has not been linked to an element in the lattice!', 'Objective PVs Missing Links!')
                return
            
        if hasattr(self, 'dummyTimer'):
            self.timer.stop()
            self.timer.deleteLater()
            del self.dummyTimer
        if hasattr(self, 'Timer'):
            self.timer.stop()
            self.timer.deleteLater()
            del self.timer
        QApplication.processEvents()
            
        self.working = True
        self.dummyTimer = Timer(50, scanner = self, f = False)
        self.timer = Timer(20, self.parent.parent.parent.progressBar, self.parent.parent.parent.statusText, self.parent.linkedMonitor, self)
        self.timer.timer.start()
        self.dummyTimer.timer.start()
        self.Scan()
        
    def Scan(self):
        selectedPVs = list(self.parent.linkedMonitor.selectedPVs.values())

        apertureBounds = [-.025, .025, -.025, .025]
        self.simulator.UpdateLatticeElements(*selectedPVs)
        latticeWithAperture = self.simulator.ApplyGlobalBeamPipeAperture(apertureBounds)
        self.simulator.lattice = latticeWithAperture

        # Define the control PV input list:
        inputControlPVCombinations = list(product(*list(self.dataDict['domains'].values())))
        # Define indices for infexing the data array
        scanRanges = [range(n) for n in list(self.parent.linkedMonitor.scanSteps.values())]
        scanIndices = list(product(*scanRanges))

        for idx, combination in enumerate(scanIndices):
            self.simulator.lattice = deepcopy(self.parent.parent.parent.lattice)
            self.simulator.UpdateLatticeElements(*selectedPVs)
            latticeWithAperture = self.simulator.ApplyGlobalBeamPipeAperture(apertureBounds)
            self.simulator.lattice = latticeWithAperture

            survivingFraction = self.simulator.Run()
            print(f'{survivingFraction * 100}% of the initial beam survived.')