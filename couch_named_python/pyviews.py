# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import sys
import os
import inspect
import base_io

from . import _set_vs, ForbiddenError, UnauthorizedError, \
        NotFoundError, Redirect

# TODO: some method for tracking loaded code version, and reloading()
# TODO: an easy method for building a design doc from a module
# TODO: docstrings

class BasePythonViewServer(base_io.BaseViewServer):
    def __init__(self, stdin, stdout):
        super(BasePythonViewServer, self).__init__(stdin, stdout)
        self.ddocs = {}
        self.reset(silent=True)

    def add_ddoc(self, doc_id, doc):
        """Add a new ddoc, or replace a ddoc"""
        self.ddocs[doc_id] = (doc, {})
        self.okay()

    def use_ddoc(self, doc_id, func_path, func_args):
        """Call a function of a previously added ddoc"""
        assert doc_id in self.ddocs
        (doc, cache) = self.ddocs[doc_id]

        # tuplify it, so that it can be used as a dict key.
        func_path = tuple(func_path)
        func_type = func_path[0]

        assert func_type in ["shows", "lists", "filters", "updates",
                             "validate_doc_update"]

        if func_path in cache:
            func = cache[func_path]
        else:
            find = doc
            for part in func_path:
                find = find[part]
            func = self.compile(find)
            cache[func_path] = func

        getattr(self, "ddoc_" + func_type)(func, func_args)

    def ddoc_shows(self, func, args):
        (doc, req) = args

        _set_vs(self, ["start", "send", "log"])
        self.response_start = None
        self.chunks = []

        try:
            value = func(doc, req)
        except NotFoundError as e:
            msg = str(e)
            if not msg:
                msg = "document not found"
            self.output("error", "not_found", msg)
        except Redirect as e:
            if e.permanent:
                c = 301
            else:
                c = 302
            self.output("resp", {"code": c, "headers": {"Location": e.url}})
        else:
            if not value:
                value = {}

            if isinstance(value, basestring):
                value = {"body": value}

            if self.chunks:
                if "body" not in value:
                    value["body"] = ""

                value["body"] = ''.join(self.chunks) + value["body"]

            if self.response_start and "headers" in self.response_start \
                    and "headers" in value:
                value["headers"].update(self.response_start["headers"])
                del self.response_start["headers"]

            if self.response_start:
                value.update(self.response_start)

            self.output("resp", value)

        self.response_start = None
        self.chunks = []

        _set_vs(None)

    def ddoc_lists(self, func, args):
        pass # TODO ddoc_lists

    def ddoc_filters(self, func, args):
        (docs, req) = args
        _set_vs(self, ["log"])
        self.output(True, [bool(func(doc, req)) for doc in docs])
        _set_vs(None)

    def ddoc_updates(self, func, args):
        pass # TODO ddoc_updates

    def ddoc_validate_doc_update(self, func, args):
        assert len(args) == 4 # newdoc, olddoc, userctx, secobj

        _set_vs(self, ["log"])

        try:
            func(*args)
        except ForbiddenError as e:
            self.single({"forbidden": str(e)})
        except UnauthorizedError as e:
            self.single({"unauthorized": str(e)})
        else:
            self.single(1)

        _set_vs(None)

    def start(self, response_start):
        assert self.response_start == None
        self.response_start = response_start

    def send(self, chunk):
        self.chunks.append(chunk)

    def get_row(self):
        pass # TODO get_row

    def reset(self, config=None, silent=False):
        """Reset state and garbage collect. Apply config, if present"""
        self.map_funcs = []
        self.emissions = None
        self.response_start = None
        self.chunks = None
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

        _set_vs(self, ["emit", "log"])
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
        # data is [[key, id], value].
        keys = [i[0] for i in data]
        values = [i[1] for i in data]
        results = []

        _set_vs(self, ["log"])

        for func_str in funcs:
            func = self.compile(func_str)
            try:
                r = func(keys, values, False)
            except:
                self.exception("reduce_runtime_error", fatal=False, func=func)
                r = None
            results.append(r)

        _set_vs(None)

        # TODO: self.query_config["reduce_limit"]
        self.output(True, results)

    def rereduce(self, funcs, values):
        """run reduce functions on some reduce function outputs"""
        results = []

        _set_vs(self, ["log"])

        for func_str in funcs:
            func = self.compile(func_str)
            try:
                r = func(None, values, True)
            except:
                self.exception("rereduce_runtime_error", fatal=False,
                               func=func)
                r = None
            results.append(r)

        _set_vs(None)

        # TODO: self.query_config["reduce_limit"]
        self.output(True, results)

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
