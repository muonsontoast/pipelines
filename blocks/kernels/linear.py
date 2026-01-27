from PySide6.QtWidgets import QGraphicsProxyWidget
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
mplstyle.use('fast')
from .kernel import Kernel

plt.rcParams['text.usetex'] = True
plt.rcParams['font.size'] = 14

class LinearKernel(Kernel):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        super().__init__(
            parent,
            proxy,
            name = kwargs.pop('name', 'Linear Kernel'),
            type = kwargs.pop('type', 'Linear Kernel'),
            size = kwargs.pop('size', [285, 250]),
            fontsize = kwargs.pop('fontSize', 12),
            # kernel-specific hyperparameters
            hyperparameters = dict(),
            **kwargs
        )

    def k(self, X1, X2):
        '''Accepts a matrix pair of X1 and X2 which are NxD arrays.\n
        Returns inner product between each pair of vectors.'''
        X1 = np.array(X1)
        X2 = np.array(X2)
        return X1 @ X2.T