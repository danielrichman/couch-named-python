# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import sys
import base_io

class BasePythonViewServer(base_io.BaseViewServer):
    def add_ddoc(self, doc_id, doc):
        """Add a new ddoc"""
        pass

    def use_ddoc(self, doc_id, func_path, func_args):
        """Call a function of a previously added ddoc"""
        pass

    def reset(self, config=None):
        """Reset state and garbage collect. Apply config, if present"""
        pass

    def add_fun(self, new_fun):
        """Add a new map function"""
        pass

    def set_lib(self, lib):
        """Set the lib"""
        pass

    def map_doc(self, doc):
        """run all map functions on a document"""
        pass

    def reduce(self, funcs, data):
        """run reduce functions on some data"""
        pass

    def rereduce(self, funcs, values):
        """run reduce functions on some reduce function outputs"""
        pass

    def compile(self, function):
        """produce something that can be executed, from a string"""
        raise NotImplementedError

class PythonNamedViewServer(BasePythonViewServer):
    def compile(self, function):
        """import a function by name"""
        pass

def main():
    PythonNamedViewServer(sys.stdin, sys.stdout).run()
