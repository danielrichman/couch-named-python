# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import sys
import traceback

try:
    # C speedups!
    import simplejson as json
except ImportError:
    import json

class BaseViewServer(object):
    """
    BaseViewServer handles IO, exception handling, and dispatching commands.

    View Server Usage::

        BaseViewServer(sys.stdin, sys.stdout).run()

    Create a subclass of BaseViewServer to do something useful! Typically,
    you would need to extend these methods:

     - add_ddoc
     - use_ddoc
     - reset
     - add_fun
     - set_lib
     - map_doc
     - reduce
     - rereduce

    In your implementations of these functions, the following methods of
    the BaseViewServer may be useful:

     - okay: replies True (i.e., command success without response)
     - respond: replies with an array, *args
     - error: reports an error to CouchDB
     - exception: reports the exception currently being handled to CouchDB
     - log: sends a log message to CouchDB

    Finally, note that add_ddoc, use_ddoc and set_lib are not actual commands
    from CouchDB. Instead, these are called from the helper functions ddoc and
    add_lib. You may wish to overide these instead if you do not like the
    helper behaviour
    """

    def __init__(self, stdin, stdout):
        self.stdin = stdin
        self.stdout = stdout

        self.commands = ["ddoc", "reset", "add_fun", "add_lib", "map_doc",
                         "reduce", "rereduce"]

    def handle_input(self, cmd_name, *args):
        """Call the correct method(*args), checking cmd_name first"""
        if cmd_name not in self.commands:
            raise ValueError("Unknown command: " + cmd_name)
        getattr(self, cmd_name)(*args)

    def ddoc(self, *args):
        """
        Checks the first argument for "new" and calls another function

        This helper will either call self.add_ddoc or self.use_ddoc
        """
        if args[0] == "new":
            self.add_ddoc(*args[1:])
        else:
            self.use_ddoc(*args)

    def add_lib(self, lib):
        """
        Helper: calls set_lib(lib)

        Since more than one lib at once is not yet used
        """
        self.set_lib(lib)

    def add_ddoc(self, doc_id, doc):
        """Add a new ddoc"""
        raise NotImplementedError

    def use_ddoc(self, doc_id, func_path, func_args):
        """Call a function of a previously added ddoc"""
        raise NotImplementedError

    def reset(self, config=None):
        """Reset state and garbage collect. Apply config, if present"""
        raise NotImplementedError

    def add_fun(self, new_fun):
        """Add a new map function"""
        raise NotImplementedError

    def set_lib(self, lib):
        """Set the current view ddoc"""
        raise NotImplementedError

    def map_doc(self, doc):
        """run all map functions on a document"""
        raise NotImplementedError

    def reduce(self, funcs, data):
        """run reduce functions on some data"""
        raise NotImplementedError

    def rereduce(self, funcs, values):
        """run reduce functions on some reduce function outputs"""
        raise NotImplementedError

    def exception(self, where="unhandled exception", fatal=True,
                  doc_id=None, func=None, log_traceback=None):
        """report the current exception to couchdb, and exit if it's fatal"""
        exc_tb = traceback.format_exc()
        info = exc_tb.splitlines()[-1].strip()

        if doc_id:
            info += ", doc_id=" + doc_id
        if func and hasattr(func, "__name__"):
            info += ", func_name=" + func.__name__
        if func and hasattr(func, "__module__"):
            info += ", func_mod=" + func.__module__

        if log_traceback is None:
            log_traceback = fatal

        if log_traceback:
            self.log(exc_tb)

        if fatal:
            self.output("error", where, info)
            sys.exit(1)
        else:
            self.log("Ignored exception ({0}): {1}".format(where, info))

    def log(self, string):
        """send a log message to couchdb"""
        self.output("log", string)

    def single(self, obj, limit=None):
        """print out a single json object"""
        line = json.dumps(obj) + "\n"

        if limit != None and len(line) > limit:
            raise ValueError("Output line length is above the limit")

        self.stdout.write(line)

    def okay(self, **kwargs):
        """report success with no output"""
        self.single(True, **kwargs)

    def output(self, *args, **kwargs):
        """print an output array (args)"""
        self.single(args, **kwargs)

    def read_line(self):
        line = self.stdin.readline()
        self._input_line_length = len(line)

        if not line:
            return None
        else:
            return json.loads(line)

    def run(self):
        """run until self.stdin is closed, reading and handling commands"""
        while True:
            try:
                obj = self.read_line()
                if obj == None:
                    break
                self.handle_input(*obj)
            except SystemExit:
                raise
            except:
                self.exception()
