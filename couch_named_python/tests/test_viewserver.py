# Copyright 2011 (C) Daniel Richman; GNU GPL 

import mox
import json
from ..viewserver import ViewServer

class JSON_NL(mox.Comparator):
    def __init__(self, obj):
        self._obj = obj
    def equals(self, rhs):
        try:
            assert rhs.endswith("\n")
            rhs = rhs[:-1]
            assert "\n" not in rhs
            obj = json.loads(rhs)
            assert obj == self._obj
        except:
            return False
        else:
            return True
    def __repr__(self):
        return "JSON_NL({0._obj!r})".format(self)

class TestViewServer(object):
    def setup(self):
        self.mocker = mox.Mox()
        self.stdin = self.mocker.CreateMock(file)
        self.stdout = self.mocker.CreateMock(file)

        self.vs = ViewServer(stdin=self.stdin, stdout=self.stdout)

    def teardown(self):
        self.mocker.UnsetStubs()

    def test_json_input_output(self):
        self.mocker.StubOutWithMock(self.vs, "handle_input")

        self.stdin.readline().AndReturn("""["reset"]\n""")
        self.vs.handle_input("reset")
        self.stdin.readline().AndReturn("""["map_doc", {"testing": true}]\n""")
        self.vs.handle_input("map_doc", {"testing": True})
        self.stdin.readline().AndReturn("")
        self.stdout.write(JSON_NL(True))
        self.stdout.write(JSON_NL([True, 1, 2, "blah", 4]))
        self.mocker.ReplayAll()

        self.vs.run()
        self.vs.okay()
        self.vs.output(True, 1, 2, "blah", 4)
        self.mocker.VerifyAll()

    def test_log(self):
        self.stdout.write(JSON_NL(["log", "A kuku!"]))
        self.stdout.write(JSON_NL(["log", "Meh"]))
        self.mocker.ReplayAll()

        self.vs.log("A kuku!")
        self.vs.log("Meh")

    def test_misc_exception(self):
        self.stdin.readline().AndReturn("invalid json, woo!")
        self.stdout.write(JSON_NL(["error", "unhandled exception",
                "ValueError: No JSON object could be decoded"]))
        self.mocker.ReplayAll()

        self.vs.run()
        self.mocker.VerifyAll()

    def test_command_exception(self):
        self.mocker.StubOutWithMock(self.vs, "handle_input")
        self.stdin.readline().AndReturn("""["hello"]\n""")
        self.vs.handle_input("hello").AndRaise(ValueError("testing"))
        self.stdout.write(JSON_NL(["error", "unhandled exception",
                "ValueError: testing"]))
        self.mocker.ReplayAll()

        self.vs.run()
        self.mocker.VerifyAll()
