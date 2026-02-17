from PySide6.QtWidgets import QGraphicsProxyWidget
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
mplstyle.use('fast')
from .kernel import Kernel

plt.rcParams['text.usetex'] = True
plt.rcParams['font.size'] = 14

class PeriodicKernel(Kernel):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        additionalHeight = 105
        hyperparameters = kwargs.pop('hyperparameters', None)
        super().__init__(
            parent,
            proxy,
            name = kwargs.pop('name', 'Periodic Kernel'),
            type = kwargs.pop('type', 'Periodic Kernel'),
            size = kwargs.pop('size', [300, 310 + additionalHeight]),
            fontsize = kwargs.pop('fontsize', 12),
            # kernel-specific hyperparameters
            hyperparameters = hyperparameters if hyperparameters is not None else {
                'scale': {
                    'description': 'magnitude of the kernel around the point',
                    'value': 1,
                    'type': 'float',
                },
                'period': {
                    'description': 'periodicity affects frequency of oscillations',
                    'value': np.array([1]),
                    'type': 'vec',
                },
                'lengthscale': {
                    'description': 'lengthscale affects how rapidly correlation decays with distance',
                    'value': np.array([1]),
                    'type': 'vec',
                },
            },
            **kwargs
        )

    def k(self, X1, X2):
        '''Accepts a matrix pair of X1 and X2 which are NxD arrays.\n
        Returns inner product between each pair of vectors.'''
        X1 = np.array(X1)
        X2 = np.array(X2)
        sigma = self.settings['hyperparameters']['scale']['value']
        period = self.settings['hyperparameters']['period']['value']
        lengthscale = self.settings['hyperparameters']['lengthscale']['value']
        X, Y = np.meshgrid(X1, X2)
        norm = np.abs(X - Y)
        return sigma ** 2 * np.exp(-2 * (np.sin(np.pi * norm / period) / lengthscale) ** 2)