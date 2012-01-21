# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import sys
import os
import inspect
import base_io

from . import _set_vs

class BasePythonViewServer(base_io.BaseViewServer):
    def __init__(self, stdin, stdout):
        super(BasePythonViewServer, self).__init__(stdin, stdout)
        self.ddocs = {}
        self.reset(silent=True)

    def add_ddoc(self, doc_id, doc):
        """Add a new ddoc"""
        self.ddocs[doc_id] = (doc, {})
        self.okay()

    def use_ddoc(self, doc_id, func_path, func_args):
        """Call a function of a previously added ddoc"""
        assert doc_id in self.ddocs
        (doc, cache) = self.ddocs[doc_id]

        func_path_parts = func_path.split(".")
        func_type = func_path_parts[0]

        assert func_type in ["shows", "lists", "filters", "updates",
                             "validate_doc_update"]

        if func_path in cache:
            func = cache[func_path]
        else:
            find = doc
            for part in func_path_parts:
                find = find[part]
            func = self.compile(find)
            cache[func_path] = func

        _set_vs(self)
        getattr(self, "ddoc_" + func_type)(func, func_args)
        _set_vs(None)

    def ddoc_shows(self, func, args):
        pass

    def ddoc_lists(self, func, args):
        pass

    def ddoc_filters(self, func, args):
        pass

    def ddoc_updates(self, func, args):
        pass

    def ddoc_validate_doc_update(self, func, args):
        assert len(args) == 3

        try:
            func(*args)
        except:
            self.exception(where="validation", func=None, fatal=False)
        else:
            self.okay(type=int)

    def reset(self, config=None, silent=False):
        """Reset state and garbage collect. Apply config, if present"""
        self.map_funcs = []
        self.emissions = None
        self.view_ddoc = {}
        if config:
            self.query_config = config
        else:
            self.query_config = {}
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
        self.emissions = None

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
