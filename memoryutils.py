from sys import getsizeof

def GetFrameArraySize(x):
    return (getsizeof(x) + sum(_.toImage().sizeInBytes() for _ in x)) / (1024 ** 2)