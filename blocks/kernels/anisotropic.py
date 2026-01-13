from PySide6.QtWidgets import QGraphicsProxyWidget
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
mplstyle.use('fast')
from .kernel import Kernel

plt.rcParams['text.usetex'] = True
plt.rcParams['font.size'] = 14

class AnisotropicKernel(Kernel):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        additionalHeight = 30
        weights = kwargs.pop('weights', np.nan)
        super().__init__(
            parent,
            proxy,
            name = kwargs.pop('name', 'Anisotropic Kernel'),
            type = kwargs.pop('type', 'Anisotropic Kernel'),
            size = kwargs.pop('size', [320, 275 + additionalHeight]),
            fontsize = kwargs.pop('fontsize', 12),
            # kernel-specific hyperparameters
            hyperparameters = {
                'weights': {
                    'description': 'NxN weight matrix',
                    # will attempt to create a diagonal matrix from the weights supplied otherwise it will be set when evaluating it on vectors.
                    'value': weights,
                    'type': 'vec',
                },
            },
            **kwargs
        )

    async def k(self, X1, X2):
        '''Accepts a matrix pair of X1 and X2 which are NxD arrays.\n
        Returns inner product between each pair of vectors.'''
        X1 = np.array(X1)
        X2 = np.array(X2)
        if np.isnan(self.settings['hyperparameters']['weights']['value']):
            w = np.eye(X1.shape[1])
        else:
            w = np.diag(self.settings['hyperparameters']['weights']['value'])
        return X1 @ w @ X2.T