try:
    from inspect import signature
except ImportError:
    # Python 3.2 and older (pip3 install funcsigs)
    from funcsigs import signature
