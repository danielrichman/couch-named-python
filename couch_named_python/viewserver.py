# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import sys
import json
import traceback

class ViewServer(object):
    def __init__(self, stdin, stdout):
        self.stdin = stdin
        self.stdout = stdout

        self.commands = ["ddoc", "reset", "add_fun", "add_lib", "map_doc",
                         "reduce", "rereduce"]

    def handle_input(self, cmd_name, *args):
        if cmd_name not in self.commands:
            raise ValueError("Unknown command: " + cmd_name)
        getattr(self, cmd_name)(*args)

    def ddoc(self, *args):
        if args[0] == "new":
            self.add_ddoc(*args[1:])
        else:
            self.use_ddoc(*args)

    def add_lib(self, lib):
        self.set_lib(lib)

    def add_ddoc(self, doc_id, doc):
        raise NotImplementedError

    def use_ddoc(self, doc_id, func_path, func_args):
        raise NotImplementedError

    def reset(self, config=None):
        raise NotImplementedError

    def add_fun(self, new_fun):
        raise NotImplementedError

    def set_lib(self, lib):
        raise NotImplementedError

    def map_doc(self, doc):
        raise NotImplementedError

    def reduce(self, funcs, data):
        raise NotImplementedError

    def rereduce(self, funcs, values):
        raise NotImplementedError

    def exception(self):
        (exc_type, exc_value, discard_tb) = sys.exc_info()
        exc_tb = traceback.format_exception_only(exc_type, exc_value)
        reason_string = exc_tb[-1].strip()
        self.output("error", "unhandled exception", reason_string)

    def log(self, string):
        self.output("log", string)

    def okay(self):
        self.stdout.write(json.dumps(True) + "\n")

    def output(self, *args):
        self.stdout.write(json.dumps(args) + "\n")

    def run(self):
        while True:
            try:
                line = self.stdin.readline()

                if not line:
                    break

                obj = json.loads(line)
                self.handle_input(*obj)
            except:
                self.exception()
                break

def main():
    vs = ViewServer(sys.stdin, sys.stdout)
    vs.run()
