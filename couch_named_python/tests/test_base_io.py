# Copyright 2011 (C) Daniel Richman; GNU GPL

import mox
import json
from ..base_io import BaseViewServer

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

class TestBaseViewServer(object):
    def setup(self):
        self.mocker = mox.Mox()
        self.stdin = self.mocker.CreateMock(file)
        self.stdout = self.mocker.CreateMock(file)

        self.vs = BaseViewServer(stdin=self.stdin, stdout=self.stdout)

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

    def vs_run_sysexit(self):
        try:
            self.vs.run()
        except SystemExit as e:
            assert e.code == 1
        else:
            raise ValueError("Expected sys.exit(1)")

    def test_misc_exception(self):
        self.stdin.readline().AndReturn("invalid json, woo!")
        self.stdout.write(JSON_NL(["error", "unhandled exception",
                "ValueError: No JSON object could be decoded"]))
        self.mocker.ReplayAll()

        self.vs_run_sysexit()
        self.mocker.VerifyAll()

    def test_command_exception(self):
        self.mocker.StubOutWithMock(self.vs, "handle_input")
        self.mocker.StubOutWithMock(self.vs, "error")
        self.stdin.readline().AndReturn("""["hello"]\n""")
        self.vs.handle_input("hello").AndRaise(ValueError("testing"))
        self.vs.error("unhandled exception", "ValueError: testing")
        self.mocker.ReplayAll()

        self.vs_run_sysexit()
        self.mocker.VerifyAll()

    def test_fatal_exception(self):
        def f(a):
            try:
                raise ValueError("test error")
            except ValueError:
                self.vs.exception(where="while compiling, for example")

        self.mocker.StubOutWithMock(self.vs, "handle_input")
        self.mocker.StubOutWithMock(self.vs, "error")
        self.stdin.readline().AndReturn("""["hello"]\n""")
        self.vs.handle_input("hello").WithSideEffects(f)
        self.vs.error("while compiling, for example", "ValueError: test error")
        self.mocker.ReplayAll()

        self.vs_run_sysexit()
        self.mocker.VerifyAll()

    def test_nonfatal_exception(self):
        def f(a):
            try:
                raise ValueError("whatever")
            except ValueError:
                self.vs.exception(where="no big deal", fatal=False)

        self.mocker.StubOutWithMock(self.vs, "handle_input")
        self.mocker.StubOutWithMock(self.vs, "error")
        self.stdin.readline().AndReturn("""["hello"]\n""")
        self.vs.handle_input("hello").WithSideEffects(f)
        self.vs.error("no big deal", "ValueError: whatever")
        self.stdin.readline().AndReturn("")
        self.mocker.ReplayAll()

        self.vs.run()
        self.mocker.VerifyAll()

    def test_error(self):
        self.stdout.write(JSON_NL(["error", "WHAT?", "SOMETHING!"]))
        self.mocker.ReplayAll()
        self.vs.error("WHAT?", "SOMETHING!")
        self.mocker.VerifyAll()

    def test_handle_dispatch(self):
        test = [("ddoc", 3), ("reset", 0), ("reset", 1), ("add_fun", 1),
                ("add_lib", 1), ("map_doc", 1), ("reduce", 2),
                ("rereduce", 2)]

        for cmd_name in set(i[0] for i in test):
            self.mocker.StubOutWithMock(self.vs, cmd_name)
        for (cmd_name, num_args) in test:
            args = [False for i in xrange(num_args)]
            getattr(self.vs, cmd_name)(*args)
        self.mocker.ReplayAll()

        for (cmd_name, num_args) in test:
            args = [False for i in xrange(num_args)]
            self.vs.handle_input(cmd_name, *args)
        self.mocker.VerifyAll()

    def test_ddoc_helper(self):
        self.mocker.StubOutWithMock(self.vs, "add_ddoc")
        self.mocker.StubOutWithMock(self.vs, "use_ddoc")

        self.vs.add_ddoc("new_doc_id", {"whatever": True})
        self.vs.use_ddoc("new_doc_id", "some.function.path", ["some", "arg"])
        self.mocker.ReplayAll()

        self.vs.ddoc("new", "new_doc_id", {"whatever": True})
        self.vs.ddoc("new_doc_id", "some.function.path", ["some", "arg"])
        self.mocker.VerifyAll()

    def test_add_lib_helper(self):
        self.mocker.StubOutWithMock(self.vs, "set_lib")
        self.vs.set_lib({"testing": True})
        self.mocker.ReplayAll()
        self.vs.add_lib({"testing": True})
        self.mocker.VerifyAll()
