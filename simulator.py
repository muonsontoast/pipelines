import at
import numpy as np
from copy import deepcopy
from . import shared

class Simulator:
    '''Handles offline simulations with the lattice.'''
    def __init__(self, numParticles = 10000, inputTwiss = None, window = None):
        self.parent = window
        self.numParticles = numParticles
        if inputTwiss is None:
            self.inputTwiss = {
                'betax': 3.731,
                'betay': 2.128,
                'alphax': -.0547,
                'alphay': -.1263,
                'emitx': 2.6e-7,
                'emity': 2.6e-7,
                'blength': 0,
                'espread': 0,
            }
        else:
            self.inputTwiss = inputTwiss

    def Run(self):
        pOut, _ = self.TrackBeam()
        return self.CalculateSurvivingFraction(pOut)

    def TrackBeam(self):
        # sigmaMat = at.sigma_matrix(betax = 3.731, betay = 2.128, alphax = -.0547, alphay = -.1263, emitx = 2.6e-7, emity = 2.6e-7, blength = 0, espread = 1.5e-2)
        sigmaMat = at.sigma_matrix(**self.inputTwiss)
        beam = at.beam(self.numParticles, sigmaMat)
        pOut, *_ = shared.lattice.track(beam, refpts = np.arange(len(shared.lattice)), nturns = 1);
        return pOut, _

    def CalculateSurvivingFraction(self, pOut, returnMask = False):
        finalState = pOut[:, :, -1].T
        survived = np.sum(~np.any(np.isnan(finalState), axis = -1))
        if returnMask:
            return survived / len(finalState[0]), ~np.isnan(pOut[0, :, -1]).ravel()
        return survived / len(finalState[0])
    
    def UpdateLatticeElements(self, *args):
        '''Accepts a list of control sliders. Their values will be applied to the lattice.'''
        for slider in args:
            # what type of element is this?
            if 'Corrector' in slider['elementName']:
                kickAngle = slider['kickAngle']
                # PyAT expects kick angles in units of radians
                kickAngle[0] *= 1e-3
                kickAngle[1] *= 1e-3
                shared.lattice[slider['elementIdx']].KickAngle = kickAngle

    def ApplyGlobalBeamPipeAperture(self, bounds):
        newLattice = deepcopy(shared.lattice)
        aperture = at.elements.Aperture('BeamPipe', bounds)

        for _ in range(len(newLattice) - 1, -1, -1):
            if newLattice[_].Length > 0:
                newLattice.insert(_, aperture)
        return newLattice