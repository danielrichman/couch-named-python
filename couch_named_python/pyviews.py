# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import sys
import os
import gc
import inspect
import base_io

from . import _set_vs

class BasePythonViewServer(base_io.BaseViewServer):
    def __init__(self, stdin, stdout):
        super(BasePythonViewServer, self).__init__(stdin, stdout)
        self.reset(silent=True)

    def add_ddoc(self, doc_id, doc):
        """Add a new ddoc"""
        pass

    def use_ddoc(self, doc_id, func_path, func_args):
        """Call a function of a previously added ddoc"""
        pass

    def reset(self, config=None, silent=False):
        """Reset state and garbage collect. Apply config, if present"""
        self.map_funcs = []
        self.emissions = []
        self.view_ddoc = {}
        if config:
            self.query_config = config
        else:
            self.query_config = {}
        gc.collect()
        if not silent:
            self.okay()

    def add_fun(self, new_fun):
        """Add a new map function"""
        self.map_funcs.append(self.compile(new_fun))
        self.okay()

    def set_lib(self, lib):
        """Set the current view ddoc"""
        self.view_ddoc = lib
        self.okay()

    def map_doc(self, doc):
        """run all map functions on a document"""
        assert self.map_funcs

        _set_vs(self)
        results = []

        for func in self.map_funcs:
            self.emissions = []

            try:
                if inspect.isgeneratorfunction(func):
                    for y in func(doc):
                        self.emit(*y)
                else:
                    func(doc)
            except:
                results.append([])
                self.exception("map_runtime_error", fatal=False,
                               doc_id=doc["_id"], func=func)
            else:
                results.append(self.emissions)

        _set_vs(None)
        self.emissions = []

        self.output(*results)

    def emit(self, key, value):
        """callback from map functions"""
        self.emissions.append([key, value])

    def reduce(self, funcs, data):
        """run reduce functions on some data"""
        pass

    def rereduce(self, funcs, values):
        """run reduce functions on some reduce function outputs"""
        pass

    def compile(self, function):
        """produce something that can be executed, from a string"""
        raise NotImplementedError

class NamedPythonViewServer(BasePythonViewServer):
    def compile(self, function):
        """import a function by name"""
        try:
            parts = function.split(".")
            if len(parts) < 2 or "" in parts:
                raise ValueError("Invalid function path")
            module = '.'.join(parts[:-1])
            name = parts[-1]
        except:
            self.exception("compile_func_name")

        try:
            __import__(module)
            f = getattr(sys.modules[module], name)
        except:
            self.exception("compile_load")

        return f

def main():
    linebuf_in = os.fdopen(sys.stdin.fileno(), 'r', 1)
    linebuf_out = os.fdopen(sys.stdout.fileno(), 'w', 1)

    NamedPythonViewServer(linebuf_in, linebuf_out).run()
