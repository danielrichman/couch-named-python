# For test_pyviews.py:TestNamedPythonViewServer:test_checks_verson

from couch_named_python import version

def func_a():
    pass

@version(2)
def func_b():
    """the second function"""
    return 50

@version(556)
def func_c(arg, aword=True):
    return "moo " + str([arg, aword])
