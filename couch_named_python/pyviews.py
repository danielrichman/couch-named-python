# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import sys
import os
import inspect
import base_io

from . import _set_vs, get_version, ForbiddenError, UnauthorizedError, \
        NotFoundError, Redirect

class BasePythonViewServer(base_io.BaseViewServer):
    """Python view server logic, with an overridable compile() method"""

    def __init__(self, stdin, stdout):
        """
        stdin, stdout: where to read and write data

        warning: they should be opened in 'line buffered' or 'unbuffered' mode
        """

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
        """execute a show function"""

        (doc, req) = args

        _set_vs(self, ["start", "send", "log"])
        self._clear_state()

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

        _set_vs(None)
        self._clear_state()

    def ddoc_lists(self, func, args):
        """execute a list function"""
        (head, req) = args

        _set_vs(self, ["start", "send", "get_row", "log"])
        self._clear_state()

        tail = None

        try:
            if inspect.isgeneratorfunction(func):
                g = func(head, req, self._get_row_generator())
                for y in g:
                    if isinstance(y, dict):
                        self.start(y)
                    else:
                        assert isinstance(y, basestring)
                        self.send(y)
            else:
                tail = func(head, req)

        except NotFoundError as e:
            msg = str(e)
            if not msg:
                msg = "document not found"
            self.output("error", "not_found", msg)
            return

        except Redirect as e:
            if e.permanent:
                c = 301
            else:
                c = 302
            # self.start will assert that start hasn't already been sent
            self.start({"code": c, "headers": {"Location": e.url}})

        if tail != None:
            self.send(tail)

        if not self.have_sent_start:
            self.get_row() # And discard

        self._send_list_chunks("end")

        self._clear_state()
        _set_vs(None)

    def ddoc_filters(self, func, args):
        """execute a filter function"""

        (docs, req) = args
        _set_vs(self, ["log"])
        self.output(True, [bool(func(doc, req)) for doc in docs])
        _set_vs(None)

    def ddoc_updates(self, func, args):
        """execute an update function"""

        (doc, req) = args
        _set_vs(self, ["log"])
        (doc, response) = func(doc, req)
        _set_vs(None)

        if isinstance(response, basestring):
            response = {"body": response}

        self.output("up", doc, response);

    def ddoc_validate_doc_update(self, func, args):
        """execute a validate_doc_update function"""

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
        """the start() callback from show functions"""
        assert self.response_start == None
        assert not self.have_sent_start
        self.response_start = response_start

    def send(self, chunk):
        """the send() callback from show functions"""
        self.chunks.append(chunk)

    def get_row(self):
        """the get_row() callback from list functions"""
        if self.list_ended:
            return None

        if not self.have_sent_start:
            self._send_list_start()
        else:
            self._send_list_chunks()

        obj = self.read_line()
        assert obj and obj[0] in ["list_row", "list_end"]

        if obj[0] == "list_end":
            self.list_ended = True
            return None
        else:
            return obj[1]

    def _get_row_generator(self):
        while True:
            row = self.get_row()
            if row == None:
                break
            yield row

    def _send_list_start(self):
        if self.response_start == None:
            self.response_start = {}
        self.output("start", self.chunks, self.response_start)
        self.chunks = []
        self.have_sent_start = True
        self.response_start = None

    def _send_list_chunks(self, label="chunks"):
        """empty self.chunks by sending them to couch"""
        self.output(label, self.chunks)
        self.chunks = []

    def _clear_state(self):
        """clear request specific state (emit, send, etc)"""
        self.emissions = []
        self.response_start = None
        self.chunks = []
        self.have_sent_start = False
        self.list_ended = False

    def reset(self, config=None, silent=False):
        """Reset state and garbage collect. Apply config, if present"""

        self.map_funcs = []
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

        _set_vs(self, ["emit", "log"])
        results = []

        for func in self.map_funcs:
            self._clear_state()

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
        self._clear_state()

        self.output(*results)

    def emit(self, key, value):
        """the emit() callback from map functions"""
        self.emissions.append([key, value])

    def _reduce_limit(self):
        """calculate the reduce limit size"""
        if "reduce_limit" not in self.query_config:
            return None
        if not self.query_config["reduce_limit"]:
            return None

        i = self._input_line_length
        return max(200, i / 2)

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

        self.output(True, results, limit=self._reduce_limit())

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

        self.output(True, results, limit=self._reduce_limit())

    def compile(self, function):
        """produce something that can be executed, from a string"""
        raise NotImplementedError

class NamedPythonViewServer(BasePythonViewServer):
    """python server that 'compiles' functions by importing the given path"""

    def compile(self, function):
        """import a function by name"""
        try:
            (function, sep, version) = function.partition("|")
            if version == "":
                version = None
            else:
                version = int(version)
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
            f_ver = get_version(f)
            if f_ver != version:
                raise ValueError("Loaded version {0!r} did not match "
                        "expected version {1!r}".format(f_ver, version))
        except:
            self.exception("compile_load")

        return f

def main():
    """main function for couch-named-python"""
    linebuf_in = os.fdopen(sys.stdin.fileno(), 'r', 1)
    linebuf_out = os.fdopen(sys.stdout.fileno(), 'w', 1)

    NamedPythonViewServer(linebuf_in, linebuf_out).run()
