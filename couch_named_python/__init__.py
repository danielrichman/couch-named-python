# Copyright 2011 (C) Daniel Richman; GNU GPL 3

# Utility functions for view functions

_current_vs = None

def emit(key, value):
    global _current_vs
    assert _current_vs
    _current_vs.emit(key, value)

def log(message):
    global _current_vs
    assert _current_vs
    _current_vs.log(message)

def _set_vs(vs):
    global _current_vs
    _current_vs = vs
