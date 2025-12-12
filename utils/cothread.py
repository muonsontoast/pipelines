'''This package will handle the importing of cothread, and allow the program to continue running even if it is not found.'''
import warnings

try:
    import aioca # asynchronous EPICS channel access client for ayncio and Python using libca via ctypes
    from asyncio import sleep

    AVAILABLE = True
    timeout = 10 # in seconds
    
    async def caget(ID, **kwargs): await aioca.caget(ID, timeout = timeout, **kwargs)
    async def caput(ID, **kwargs): await aioca.caput(ID, timeout = timeout, **kwargs)
    async def Sleep(t): await sleep(t)
except ImportError:
    AVAILABLE = False
    warnings.warn('cothread is not available, online mode for the pipelines app will be disabled. The package is either missing, or you\'re trying to run the app on a Windows machine but cothread only supports Linux Python installs.')