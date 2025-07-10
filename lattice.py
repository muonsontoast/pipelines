import at
from at import get_s_pos, linopt2
from at import elements as emnts
import numpy as np
from copy import deepcopy
import pandas as pd
from datetime import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt

loadedLattice = None
sElementList = None

def GetLatticeInfo(lattice):
    elements = [[None for _ in range(3)] for _ in range(len(lattice))]
    for idx, element in enumerate(lattice):
        elements[idx][0] = element.FamName
        elements[idx][1] = type(element).__name__
        elements[idx][2] = sElementList[idx]
    elements = pd.DataFrame(elements)
    elements.columns = ['Name', 'Type', 's (m)']
    return elements

def DrawBeam(beamIn, xlim = 3, ylim = 3, pxlim = 1.25, pylim = 1.25, numBins = 50, marginalScaleFactor = .075, marginalColor = 'tab:purple'):
    fig, ax = plt.subplots(1, 2, figsize = (11.5, 5))
    fig.subplots_adjust(wspace = .25)
    beam = deepcopy(beamIn)
    beam[0, :] *= 1e3
    beam[1, :] *= 1e3
    beam[2, :] *= 1e3
    beam[3, :] *= 1e3
    padX, padY, padPx, padPy = .025 * 2 * xlim, .025 * 2 * ylim, .025 * 2 * pxlim, .025 * 2 * pylim
    hist, x, y, p = plt.hist2d(beam[0, :], beam[2, :], bins = numBins, range = ((-xlim, xlim), (-ylim, ylim)), alpha = 0)
    ax[0].imshow(hist.T, origin = 'lower', extent = (-xlim, xlim, -ylim, ylim), interpolation = 'bicubic', cmap = 'inferno')

    histx, binsx = np.histogram(beam[0, :], range = (-xlim - padX, xlim + padX), bins = numBins)
    histx = histx / histx.max() * 2 * ylim * marginalScaleFactor
    binsx = .5 * (binsx[1:] + binsx[:-1])
    ax[0].fill_between(binsx, -ylim, histx + -ylim, alpha = .5, color = marginalColor, zorder = 10)
    histx, binsx = np.histogram(beam[2, :], range = (-ylim - padY, ylim + padY), bins = numBins)
    histx = histx / histx.max() * 2 * xlim * marginalScaleFactor
    binsx = .5 * (binsx[1:] + binsx[:-1])
    ax[0].fill_betweenx(binsx, -xlim * np.ones(len(histx)) - .01, -xlim * np.ones(len(histx)) + histx, alpha = .5, color = marginalColor, zorder = 10)

    ax[0].set_xlabel(r'$x$ (mm)')
    ax[0].set_ylabel(r'$y$ (mm)')
    ax[0].set_xlim(-xlim, xlim)
    ax[0].set_ylim(-ylim, ylim)
    ax[0].set_title(r'Beam Distribution in $x-y$')

    hist, x, y, p = plt.hist2d(beam[1, :], beam[3, :], bins = numBins, range = ((-pxlim, pxlim), (-pylim, pylim)), alpha = 0)
    ax[1].imshow(hist.T, origin = 'lower', extent = (-pxlim, pxlim, -pylim, pylim), interpolation = 'bicubic', cmap = 'inferno')

    histx, binsx = np.histogram(beam[1, :], range = (-pxlim - padPx, pxlim + padPx), bins = numBins)
    histx = histx / histx.max() * 2 * pylim * marginalScaleFactor
    binsx = .5 * (binsx[1:] + binsx[:-1])
    ax[1].fill_between(binsx, -pylim, histx + -pylim, alpha = .5, color = marginalColor, zorder = 10)
    histx, binsx = np.histogram(beam[3, :], range = (-pylim - padPy, pylim + padPy), bins = numBins)
    histx = histx / histx.max() * 2 * pxlim * marginalScaleFactor
    binsx = .5 * (binsx[1:] + binsx[:-1])
    ax[1].fill_betweenx(binsx, -pxlim * np.ones(len(histx)) - .01, -pxlim * np.ones(len(histx)) + histx, alpha = .5, color = marginalColor, zorder = 10)
    ax[1].set_xlim(-pxlim, pxlim)
    ax[1].set_ylim(-pylim, pylim)
    ax[1].set_xlabel(r'$p_x$ (mrad)')
    ax[1].set_ylabel(r'$p_y$ (mrad)')
    ax[1].set_title(r'Beam Distribution in $p_x-p_y$')

def DrawLattice(canvas, lattice, ylim = None, alpha = 1, scale = .15, offset = 0, validTypes = [], showTwiss = False):
    # ax = canvas.axes[0]
    canvas.axes[0] = canvas.fig.add_subplot(111)
    ax = canvas.axes[0]
    ax.set_yticks([])
    ax.set_yticklabels([])
    s = 0
    cmap = {
        'Dipole': 'tab:red',
        'Quadrupole': 'navy',
        'Sextupole': 'tab:green',
        'Octupole': 'tab:yellow',
        'Octupole': 'tab:orange',
        'RF': 'darkgrey',
        'Corrector': 'grey',
        'BPM': 'purple',
        'SCREEN': 'black',
        'COLL': 'black',
    }
    if ylim is not None:
        rectHeight = scale * (ylim[1] - ylim[0])
        offset = ylim[0] + offset * (ylim[1] - ylim[0])
    else:
        rectHeight = 1.25
        offset = 0
    usedLabels = []
    def DrawQuad(quadType, length, ax, color, alpha = alpha):
        if quadType == 'Focusing':
            verts = [
                (s + .5 * length, offset -.5 * rectHeight),
                (s, offset),
                (s + .5 * length, offset + .5 * rectHeight),
                (s + length, offset),
            ]
            label = r'$\mathrm{QF}_x$'
        else: # defocusing
            color = 'royalblue'
            verts = [
                (s, offset -.5 * rectHeight),
                (s + .5 * length, offset),
                (s, offset + .5 * rectHeight),
                (s + length, offset + .5 * rectHeight),
                (s + .5 * length, offset),
                (s + length, offset -.5 * rectHeight),
            ]
            label = r'$\mathrm{QD}_x$'
        if label not in usedLabels:
            ngon = mpl.patches.Polygon(verts, closed = True, color = color, alpha = alpha, zorder = 10, label = label, picker = 15, gid = f'{name}{_}')
            usedLabels.append(label)
        else:
            ngon = mpl.patches.Polygon(verts, closed = True, color = color, alpha = alpha, zorder = 10, picker = 15, gid = f'{name}{_}')
        ax.add_patch(ngon)

    displayedElement = False

    canvas.axes[1] = canvas.axes[0].twinx()
    canvas.axes[2] = canvas.axes[0].twinx()

    if not showTwiss:
        for ax in canvas.axes[1:]:
            ax.set_yticks([])
            ax.set_yticklabels([])

    if showTwiss:
        # Extract the twiss parameters of the beamline
        # twiss is a rec array (numpy array that can be indexed like ndarray.abc = xyz) with an entry for each lattice element
        twiss = linopt2(lattice, refpts = np.arange(len(lattice) + 1)) # twiss parameters contained in final returned element (idx 2)
        # Plot the twiss parameters along the beamline
        sPos, betaX, betaY, dispersionX, dispersionY = np.empty(len(twiss[2])), np.empty(len(twiss[2])), np.empty(len(twiss[2])), np.empty(len(twiss[2])), np.empty(len(twiss[2]))

        for _, t in enumerate(twiss[2]):
            sPos[_] = t.s_pos
            betaX[_] = t.beta[0]
            betaY[_] = t.beta[1]
            dispersionX[_] = t.dispersion[0]
            dispersionY[_] = t.dispersion[1]
        canvas.axes[1].set_ylabel(r'$\beta$ (m)')
        canvas.axes[1].minorticks_on()
        canvas.axes[1].yaxis.set_ticks_position('left')   # y-ticks on the left
        canvas.axes[1].yaxis.set_label_position('left')
        canvas.axes[2].set_ylabel(r'$\eta$ (m)')
        canvas.axes[2].minorticks_on()
        canvas.axes[1].plot(sPos, betaX, color = 'blue', label = r'$\beta_x$')
        canvas.axes[1].plot(sPos, betaY, color = 'red', label = r'$\beta_y$')
        canvas.axes[1].set_ylim(bottom = 0)
        canvas.axes[2].plot(sPos, dispersionX, color = 'green', label = r'$\eta_x$')

    for _, element in enumerate(lattice):
        length = getattr(element, 'Length', 0)
        name = type(element).__name__
        s += length

        if name not in validTypes: # Triggers if the element is either excluded from the filter list or a marker (BPM, Screen, Collimator)
            if element.FamName not in validTypes: # Check if the FamName is in the filter list (distinguishing feature for markers)
                continue
            else:
                name = element.FamName

        for key in cmap:
            if key == name:
                displayedElement = True
                if key == 'Quadrupole':
                    quadType = 'Focusing' if getattr(element, 'K') > 0 else ''
                    DrawQuad(quadType, length, canvas.axes[0], cmap[key], alpha)
                else:
                    if key not in usedLabels:
                        if key == 'SCREEN':
                            label = 'Screen'
                        elif key == 'COLL':
                            label = 'Collimator'
                        else:
                            label = key
                        rect = mpl.patches.Rectangle((s, offset -.5 * rectHeight), length, rectHeight, color = cmap[key], alpha = alpha, zorder = 10, label = rf'$\mathrm{{{label}}}$', picker = 15, gid = f'{name}{_}')
                        usedLabels.append(key)
                    else:
                        rect = mpl.patches.Rectangle((s, offset -.5 * rectHeight), length, rectHeight, color = cmap[key], alpha = alpha, zorder = 10, picker = 15, gid = f'{name}{_}')
                    canvas.axes[0].add_patch(rect)
                break

    canvas.axes[0].axhline(0, color = 'black', lw = 1)

    if showTwiss:
        # combine labels across axes
        handles1, labels1 = canvas.axes[0].get_legend_handles_labels()
        handles2, labels2 = canvas.axes[1].get_legend_handles_labels()
        handles3, labels3 = canvas.axes[2].get_legend_handles_labels()
        # Combine
        handles = handles1 + handles2 + handles3
        labels = labels1 + labels2 + labels3
    else:
        handles, labels = canvas.axes[0].get_legend_handles_labels()
    
    canvas.axes[0].legend(loc = 'center', bbox_to_anchor = (.5, 1.15), handles = handles, labels = labels, ncols = 10, framealpha = 0, frameon = True, fontsize = 8, edgecolor = 'black')
    canvas.axes[0].set_xlim(0, s + 1e-10)
    canvas.axes[0].set_ylim(-1, 1)
    # beam pipe radius in LTB is +- 25 mm

def DrawTrajectories(lattice, pOut, **kwargs):
    apertureBounds = kwargs.get('apertureBounds', None)

    fig, ax = plt.subplots(2, 2, figsize = (12, 10))
    fig.subplots_adjust(wspace = .25, hspace = .35)

    sElementList = at.lattice.get_s_pos(lattice)
    pOutNew = pOut * 1e3
    colors = mpl.cm.tab10(np.linspace(0, 1, 10))

    historiesX = pOutNew[0, :, :].T[0].T
    historiesY = pOutNew[2, :, :].T[0].T
    historiesPx = pOutNew[1, :, :].T[0].T
    historiesPy = pOutNew[3, :, :].T[0].T

    segments = np.array([np.column_stack((sElementList[:-1], xi)) for xi in historiesX])
    lineCollection = mpl.collections.LineCollection(segments, linewidths = .5, colors = colors, zorder = -1)
    ax[0, 0].add_collection(lineCollection)
    ax[0, 0].set_xlim(sElementList[:-1].min(), sElementList[:-1].max())
    ax[0, 0].set_ylim(-40, 40)

    segments = np.array([np.column_stack((sElementList[:-1], xi)) for xi in historiesY])
    lineCollection = mpl.collections.LineCollection(segments, linewidths = .5, colors = colors, zorder = -1)
    ax[0, 1].add_collection(lineCollection)
    ax[0, 1].set_xlim(sElementList[:-1].min(), sElementList[:-1].max())
    ax[0, 1].set_ylim(-40, 40)

    segments = np.array([np.column_stack((sElementList[:-1], xi)) for xi in historiesPx])
    lineCollection = mpl.collections.LineCollection(segments, linewidths = .5, colors = colors, zorder = -1)
    ax[1, 0].add_collection(lineCollection)
    ax[1, 0].set_xlim(sElementList[:-1].min(), sElementList[:-1].max())
    ax[1, 0].set_ylim(-10, 10)

    segments = np.array([np.column_stack((sElementList[:-1], xi)) for xi in historiesPy])
    lineCollection = mpl.collections.LineCollection(segments, linewidths = .5, colors = colors, zorder = -1)
    ax[1, 1].add_collection(lineCollection)
    ax[1, 1].set_xlim(sElementList[:-1].min(), sElementList[:-1].max())
    ax[1, 1].set_ylim(-10, 10)

    ylim00 = ylim01 = ylim10 = ylim11 = 0

    if apertureBounds is not None:
        ylim00 = list(ax[0, 0].get_ylim())
        ylim01 = list(ax[0, 1].get_ylim())
        ylim10 = list(ax[1, 0].get_ylim())
        ylim11 = list(ax[1, 1].get_ylim())

        apertureThicknessSF = .005

        apertureThickness00 = apertureThicknessSF * (ylim00[1] - ylim00[0])
        apertureThickness01 = apertureThicknessSF * (ylim01[1] - ylim01[0])

        # Draw aperture
        apertureBottom00 = plt.Rectangle((0, apertureBounds[0] * 1000 - apertureThickness00), sElementList[-1], apertureThickness00, color = 'black')
        apertureTop00 = plt.Rectangle((0, apertureBounds[1] * 1000), sElementList[-1], apertureThickness00, color = 'black')
        apertureBottom01 = plt.Rectangle((0, apertureBounds[2] * 1000 - apertureThickness01), sElementList[-1], apertureThickness01, color = 'black')
        apertureTop01 = plt.Rectangle((0, apertureBounds[3] * 1000), sElementList[-1], apertureThickness01, color = 'black')

        ax[0, 0].add_patch(plt.Rectangle((0, ylim00[0]), sElementList[-1], apertureBounds[0] * 1000 - ylim00[0], color = 'white'))
        ax[0, 0].add_patch(plt.Rectangle((0, apertureBounds[1] * 1000), sElementList[-1], ylim00[1] - apertureBounds[1] * 1000, color = 'white'))
        ax[0, 1].add_patch(plt.Rectangle((0, ylim01[0]), sElementList[-1], apertureBounds[2] * 1000 - ylim01[0], color = 'white'))
        ax[0, 1].add_patch(plt.Rectangle((0, apertureBounds[3] * 1000), sElementList[-1], ylim01[1] - apertureBounds[3] * 1000, color = 'white'))

        ax[0, 0].add_patch(apertureBottom00)
        ax[0, 0].add_patch(apertureTop00)
        ax[0, 1].add_patch(apertureBottom01)
        ax[0, 1].add_patch(apertureTop01)

    # Draw lattice components
    # DrawLattice(ax[0, 0], lattice, ylim00, 1, .1, .075)
    # DrawLattice(ax[0, 1], lattice, ylim01, 1, .1, .075)
    # DrawLattice(ax[1, 0], lattice, ylim10, 1, .1, .075)
    # DrawLattice(ax[1, 1], lattice, ylim11, 1, .1, .075)

    # Assign labels, etc.
    ax[0, 0].set_ylabel(r'$x$ (mm)')
    ax[0, 0].set_xlabel(r'$s$ (m)')
    ax[0, 1].set_ylabel(r'$y$ (mm)')
    ax[0, 1].set_xlabel(r'$s$ (m)')
    ax[1, 0].set_ylabel(r'$p_x$ (mrad)')
    ax[1, 0].set_xlabel(r'$s$ (m)')
    ax[1, 1].set_ylabel(r'$p_y$ (mrad)')
    ax[1, 1].set_xlabel(r'$s$ (m)')
    ax[0, 0].set_title(r'$x$-Coordinate along LTB Injection Line')
    ax[0, 1].set_title(r'$y$-Coordinate along LTB Injection Line')                    
    ax[1, 0].set_title(r'$p_x$-Coordinate along LTB Injection Line')
    ax[1, 1].set_title(r'$p_y$-Coordinate along LTB Injection Line')

    ax[0, 0].grid(alpha = .35)
    ax[0, 1].grid(alpha = .35)
    ax[1, 0].grid(alpha = .35)
    ax[1, 1].grid(alpha = .35)

# def ApplyCorrectorStrengths(lattice, cVec = np.zeros(12)):
#     '''cVec should take the form [HSTR1, ..., VSTR1, ...]'''
#     cVec = list(cVec)
#     HSTRIdxs = lattice.get_uint32_index('HSTR')
#     VSTRIdxs = lattice.get_uint32_index('VSTR')
#     cVecHSTR = cVec[:len(HSTRIdxs)]
#     cVecVSTR = cVec[len(HSTRIdxs):]
    
#     for i, idx in enumerate(HSTRIdxs):
#         lattice[idx].KickAngle[0] = cVecHSTR[i]
#     for i, idx in enumerate(VSTRIdxs):
#         lattice[idx].KickAngle[1] = cVecVSTR[i]

def LoadLattice(pth):
    return at.load_mat(pth, mat_key = 'THERING', energy = 1e8, periodicity = 0)

def UpdateAperture(apertureBounds, lattice, disable6D = True):
    latticeWithFinalAperture = deepcopy(lattice)
    latticeWithFinalAperture.append(emnts.Aperture('AP', apertureBounds))
    latticeWithFinalAperture.append(emnts.Drift('Drift', 1e-5)) 
    if disable6D:
        latticeWithFinalAperture.disable_6d()
    return latticeWithFinalAperture