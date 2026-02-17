from PySide6.QtWidgets import QGraphicsProxyWidget
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
mplstyle.use('fast')
from .kernel import Kernel

plt.rcParams['text.usetex'] = True
plt.rcParams['font.size'] = 14

class MaternKernel(Kernel):
    def __init__(self, parent, proxy: QGraphicsProxyWidget, **kwargs):
        '''Accepts `name` and `type` overrides for entity.'''
        additionalHeight = 104
        hyperparameters = kwargs.pop('hyperparameters', None)
        super().__init__(
            parent,
            proxy,
            name = kwargs.pop('name', 'Matérn Kernel'),
            type = kwargs.pop('type', 'Matern Kernel'),
            size = kwargs.pop('size', [300, 310 + additionalHeight]),
            fontsize = kwargs.pop('fontsize', 12),
            # kernel-specific hyperparameters
            hyperparameters = hyperparameters if hyperparameters is not None else {
                'scale': {
                    'description': 'magnitude of the kernel around the point',
                    'value': 1,
                    'type': 'float',
                },
                'lengthscale': {
                    'description': 'lengthscale affects how rapidly correlation decays with distance',
                    'value': np.array([1]),
                    'type': 'vec',
                },
                'smoothness': {
                    'description': 'controls smoothness at kernel centre',
                    'value': 1/2,
                    'type': 'float',
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
        lengthscale = self.settings['hyperparameters']['lengthscale']['value']
        X, Y = np.meshgrid(X1, X2)
        norm = np.abs(X - Y)
        nu = self.settings['hyperparameters']['smoothness']['value']
        if nu == 1/2:
            return sigma ** 2 * np.exp(-norm / lengthscale)
        elif nu == 3/2:
            frac = np.sqrt(3) * norm / lengthscale
            return sigma ** 2 * (1 + frac) * np.exp(-frac)
        elif nu == 5/2:
            frac = np.sqrt(5) * norm / lengthscale
            return sigma ** 2 * (1 + frac + 1/3 * frac ** 2) * np.exp(-frac)
            