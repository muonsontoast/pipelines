'''This package will handle the importing of cothread, and allow the program to continue running even if it is not found.'''
import warnings

try:
    import cothread
    AVAILABLE = True
    def Sleep(t): cothread.Sleep(t)
    def caget(ID): cothread.caget(ID)
    def caput(ID): cothread.caput(ID)
except ImportError:
    AVAILABLE = False
    warnings.warn('cothread is not available, online mode for the pipelines app will be disabled. The package is either missing, or you\'re trying to run the app on a Windows machine but cothread only supports Linux Python installs.')