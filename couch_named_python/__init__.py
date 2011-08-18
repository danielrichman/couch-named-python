# TODO header.

import sys
import json
import traceback

class ViewServer:
    def __init__(self, stdin=sys.stdin, stdout=sys.stdout):
        self.stdin = stdin
        self.stdout = stdout

    def handle_input(self, **args):
        pass

    def exception(self, code="unhandled exception"):
        (exc_type, exc_value, discard_tb) = sys.exc_info()
        exc_tb = traceback.format_exception_only(exc_type, exc_value)
        reason_string = exc_tb[-1].strip()
        self.output({"error": code, "reason": reason_string})

    def log(self, string):
        self.output(["log", string])

    def output(self, obj):
        self.stdout.write(json.dumps(obj) + "\n")

    def run(self):
        while True:
            line = self.stdin.readline()

            if not line:
                break

            try:
                obj = json.loads(line)
                self.handle_input(*obj)
            except:
                self.exception()
                break

def main():
    vs = ViewServer()
    vs.run()
