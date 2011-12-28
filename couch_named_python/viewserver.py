# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import sys
import json
import traceback

class ViewServer(object):
    def __init__(self, stdin, stdout):
        self.stdin = stdin
        self.stdout = stdout

    def handle_input(self, **args):
        pass

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
