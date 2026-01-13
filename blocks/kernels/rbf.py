from PySide6.QtWidgets import QGraphicsProxyWidget
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
mplstyle.use('fast')
from .kernel import Kernel

plt.rcParams['text.usetex'] = True
plt.rcParams['font.size'] = 14

class RBFKernel(Kernel):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        additionalHeight = 64
        sigma = kwargs.pop('sigma', np.nan)
        lengthscale = kwargs.pop('lengthscale', np.nan)
        super().__init__(
            parent,
            proxy,
            name = kwargs.pop('name', 'RBF Kernel'),
            type = kwargs.pop('type', 'RBF Kernel'),
            size = kwargs.pop('size', [320, 275 + additionalHeight]),
            fontsize = kwargs.pop('fontsize', 12),
            # kernel-specific hyperparameters
            hyperparameters = {
                'scale': {
                    'description': 'magnitude of the kernel around the point',
                    'value': sigma,
                    'type': 'float',
                },
                'lengthscale': {
                    'description': 'lengthscale affects how rapidly correlation decays with distance',
                    'value': lengthscale,
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
        self.settings['hyperparameters']['scale']['value'] = 1 if np.isnan(self.settings['hyperparameters']['scale']['value']) else self.settings['hyperparameters']['scale']['value']
        sigma = self.settings['hyperparameters']['scale']['value']
        self.settings['hyperparameters']['lengthscale']['value'] = np.ones(X1.shape[1]) if np.isnan(self.settings['hyperparameters']['lengthscale']['value']) else self.settings['hyperparameters']['lengthscale']['value']
        lengthscale = self.settings['hyperparameters']['lengthscale']['value']
        X, Y = np.meshgrid(X1, X2)
        norm = np.abs(X - Y)
        return sigma ** 2 * np.exp(-2 * (norm / lengthscale) ** 2)