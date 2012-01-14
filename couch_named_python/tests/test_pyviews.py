# Copyright 2011 (C) Daniel Richman; GNU GPL 3

import mox
import sys
import gc
import os
from ..pyviews import BasePythonViewServer, NamedPythonViewServer, main
from .. import pyviews

class TestBasePythonViewServer(object):
    def setup(self):
        self.mocker = mox.Mox()
        self.vs = BasePythonViewServer(None, None)
        self.mocker.StubOutWithMock(self.vs, "compile")
        self.mocker.StubOutWithMock(self.vs, "okay")
        self.mocker.StubOutWithMock(self.vs, "output")
        self.mocker.StubOutWithMock(self.vs, "log")

    def teardown(self):
        self.mocker.UnsetStubs()

    def test_add_ddoc(self):
        pass

    def test_use_ddoc(self):
        pass

    def test_reset(self):
        self.mocker.StubOutWithMock(gc, "collect")

        self.test_add_fun()
        self.mocker.ResetAll()
        assert len(self.vs.map_funcs) == 2

        gc.collect()
        self.vs.okay()
        self.mocker.ReplayAll()

        self.vs.reset({"reduce_limit": True})
        assert len(self.vs.map_funcs) == 0
        assert self.vs.query_config == {"reduce_limit": True}

        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.test_map_doc()
        self.mocker.ResetAll()

        gc.collect()
        self.vs.okay()
        self.mocker.ReplayAll()

        self.vs.reset()
        assert self.vs.query_config == {}
        self.mocker.VerifyAll()

    def test_add_fun(self):
        def my_map(doc):
            pass
        def my_map2(doc):
            pass

        self.vs.compile("something that describes my_map").AndReturn(my_map)
        self.vs.okay()
        self.vs.compile("another map").AndReturn(my_map2)
        self.vs.okay()
        self.mocker.ReplayAll()

        self.vs.add_fun("something that describes my_map")
        assert self.vs.map_funcs == [my_map]
        self.vs.add_fun("another map")
        assert self.vs.map_funcs == [my_map, my_map2]
        self.mocker.VerifyAll()

    def test_set_lib(self):
        self.vs.okay()
        self.mocker.ReplayAll()
        self.vs.set_lib({"some_ddoc_data": "whatever"})
        assert self.vs.view_ddoc == {"some_ddoc_data": "whatever"}
        self.mocker.VerifyAll()

    def test_map_doc(self):
        def map_one(doc):
            from couch_named_python import emit
            for i in xrange(1, 4):
                emit(doc["word"] + " " + str(i), i * i)
        def map_two(doc):
            if doc["word"] == "cow":
                yield False, doc["something"]
                yield True, doc["something"]
        def map_three(doc):
            from couch_named_python import log
            if doc["word"] == "cow":
                yield doc["nonexistant"], False
            yield doc["something"], None
            log("From view test")

        docs = [{"_id": "d1", "word": "hippo", "something": {"123": True}},
                {"_id": "d2", "word": "cow", "something": [4, 5, 6]},
                {"_id": "d3", "word": "cow", "something": [5, 7, 8]}]

        self.vs.compile("one").AndReturn(map_one)
        self.vs.okay()
        self.vs.compile("two").AndReturn(map_two)
        self.vs.okay()
        self.vs.compile("three").AndReturn(map_three)
        self.vs.okay()

        self.vs.log("From view test")
        self.vs.output([["hippo 1", 1], ["hippo 2", 4], ["hippo 3", 9]],
                       [],
                       [[{"123": True}, None]])
        self.vs.log("Ignored error, map_runtime_error, "
                    "KeyError: 'nonexistant', doc_id=d2, func_name=map_three, "
                    "func_mod=couch_named_python.tests.test_pyviews")
        self.vs.output([["cow 1", 1], ["cow 2", 4], ["cow 3", 9]],
                       [[False, [4, 5, 6]], [True, [4, 5, 6]]],
                       [])
        self.vs.log("Ignored error, map_runtime_error, "
                    "KeyError: 'nonexistant', doc_id=d3, func_name=map_three, "
                    "func_mod=couch_named_python.tests.test_pyviews")
        self.vs.output([["cow 1", 1], ["cow 2", 4], ["cow 3", 9]],
                       [[False, [5, 7, 8]], [True, [5, 7, 8]]],
                       [])

        self.mocker.ReplayAll()

        self.vs.add_fun("one")
        self.vs.add_fun("two")
        self.vs.add_fun("three")
        for d in docs:
            self.vs.map_doc(d)
        self.mocker.VerifyAll()

    def test_reduce(self):
        pass

    def test_rereduce(self):
        pass

class TestNamedPythonViewServer(object):
    def setup(self):
        self.mocker = mox.Mox()
        self.vs = NamedPythonViewServer(None, None)
        self.mocker.StubOutWithMock(self.vs, "output")

    def teardown(self):
        self.mocker.UnsetStubs()

    def test_compile(self):
        name = "couch_named_python.tests.example_mod"
        assert name not in sys.modules
        f = self.vs.compile(name + ".func_a")
        assert name in sys.modules

        assert f() == "test function A"

    def compile_sysexit(self, what):
        try:
            self.vs.compile(what)
        except SystemExit as e:
            assert e.code == 1
        else:
            raise ValueError("Expected sys.exit(1)")

    def test_bad_name(self):
        for bad_string in ["asdf..fghj", "", ".", ".asdf.dfgh", "jkg.asdf.",
                           "only_one_part"]:
            self.vs.output("error", "compile_func_name",
                           "ValueError: Invalid function path")
            self.mocker.ReplayAll()

            self.compile_sysexit(bad_string)

            self.mocker.VerifyAll()
            self.mocker.ResetAll()

    def test_nonexistant(self):
        self.vs.output("error", "compile_load",
                       "ImportError: No module named couch_named_python_other")
        self.mocker.ReplayAll()

        self.compile_sysexit("couch_named_python_other.asdf")
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.vs.output("error", "compile_load",
                       "AttributeError: 'module' object has no attribute "
                       "'other_function'")
        self.mocker.ReplayAll()

        self.compile_sysexit("couch_named_python.tests.example_mod."
                             "other_function")
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

class TestMain:
    def setup(self):
        self.mocker = mox.Mox()
        self.mocker.StubOutWithMock(os, "fdopen")
        self.sys_stdin = sys.stdin
        self.sys_stdout = sys.stdout
        sys.stdin = self.mocker.CreateMock(file)
        sys.stdout = self.mocker.CreateMock(file)
        self.vs = self.mocker.CreateMock(NamedPythonViewServer)
        self.mocker.StubOutWithMock(pyviews, "NamedPythonViewServer")

    def teardown(self):
        sys.stdin = self.sys_stdin
        sys.stdout = self.sys_stdout
        self.mocker.UnsetStubs()

    def test_main(self):
        sin = object()
        sout = object()

        sys.stdin.fileno().AndReturn(1234)
        os.fdopen(1234, 'r', 1).AndReturn(sin)
        sys.stdout.fileno().AndReturn(7890)
        os.fdopen(7890, 'w', 1).AndReturn(sout)

        pyviews.NamedPythonViewServer(sin, sout).AndReturn(self.vs)
        self.vs.run()

        self.mocker.ReplayAll()

        main()
        self.mocker.VerifyAll()
