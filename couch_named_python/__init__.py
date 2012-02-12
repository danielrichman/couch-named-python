# Copyright 2011 (C) Daniel Richman; GNU GPL 3

# Utility functions for view functions

_current_vs = None
_current_funcs = None

def emit(key, value):
    global _current_vs
    assert _can("emit")
    _current_vs.emit(key, value)

def log(message):
    global _current_vs
    assert _can("log")
    _current_vs.log(message)

def _can(func):
    global _current_vs, _current_funcs
    return _current_vs and func in _current_funcs

def _set_vs(vs, funcs=[]):
    global _current_vs, _current_funcs
    _current_vs = vs
    _current_funcs = funcs

class Forbidden(Exception):
    pass

class Unauthorized(Exception):
    pass

Unauthorised = Unauthorized # :-)
