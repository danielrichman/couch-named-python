# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import mox

class EqIfIn(mox.Comparator):
    def __init__(self, obj):
        self._obj = obj
    def equals(self, rhs):
        return self._obj in rhs
    def __repr__(self):
        return "EqIfIn({0})".format(self._obj)
