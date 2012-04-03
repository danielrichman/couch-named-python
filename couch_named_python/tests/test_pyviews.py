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
        self.mocker.StubOutWithMock(self.vs, "single")
        self.mocker.StubOutWithMock(self.vs, "okay")
        self.mocker.StubOutWithMock(self.vs, "output")
        self.mocker.StubOutWithMock(self.vs, "log")

    def teardown(self):
        self.mocker.UnsetStubs()

    def test_add_ddoc(self):
        self.vs.okay()
        self.vs.okay()
        self.mocker.ReplayAll()
        self.vs.add_ddoc("test_designdoc", {"test": True})
        self.vs.add_ddoc("second_doc", {"second": True})
        assert self.vs.ddocs["test_designdoc"] == ({"test": True}, {})
        assert self.vs.ddocs["second_doc"] == ({"second": True}, {})
        self.mocker.VerifyAll()

    def test_use_ddoc(self):
        self.mocker.StubOutWithMock(self.vs, "ddoc_shows")
        self.mocker.StubOutWithMock(self.vs, "ddoc_lists")
        self.mocker.StubOutWithMock(self.vs, "ddoc_filters")
        self.mocker.StubOutWithMock(self.vs, "ddoc_updates")
        self.mocker.StubOutWithMock(self.vs, "ddoc_validate_doc_update")
        
        doc_a = {"shows": {"show1": "function:1", "show2": "function:2"},
                 "lists": {"list3": "function:3"},
                 "updates": {"update4": "function:4"}}
        doc_b = {"filters": {"filter5": "function:5"},
                 "validate_doc_update": "function:6"}

        # doc_id, func_path, func, expect compilation
        tests = [("example", ["shows","show1"], "function:1", True),
                 ("example", ["shows","show2"], "function:2", True),
                 ("example", ["shows","show2"], "function:2", False),
                 ("example", ["shows","show1"], "function:1", False),
                 ("elpmaxe", ["validate_doc_update"], "function:6", True),
                 ("example", ["shows","show2"], "function:2", False),
                 ("elpmaxe", ["filters","filter5"], "function:5", True),
                 ("example", ["updates","update4"], "function:4", True),
                 ("example", ["lists","list3"], "function:3", True),
                 ("elpmaxe", ["filters","filter5"], "function:5", False)]

        self.vs.okay()
        self.vs.okay()

        for (doc_id, func_path, func, expect_compile) in tests:
            c = {"a compiled function": True, "sauce": func}
            func_type = func_path[0]
            if expect_compile:
                self.vs.compile(func).AndReturn(c)
            h = "ddoc_" + func_type
            getattr(self.vs, h)(c, ["args for", func_path])

        self.mocker.ReplayAll()

        self.vs.add_ddoc("example", doc_a)
        self.vs.add_ddoc("elpmaxe", doc_b)

        for (doc_id, func_path, func, expect_compile) in tests:
            self.vs.use_ddoc(doc_id, func_path, ["args for", func_path])

        self.mocker.VerifyAll()

    def test_validate_doc_update(self):
        def f(new, old, user, secobj):
            if new == 1:
                assert old == 2
                assert user == 3
                assert secobj == 4
            elif new == "bad":
                from couch_named_python import log, ForbiddenError
                log("Some sort of log")
                raise ForbiddenError("Some sort of error.")
            elif new == "what":
                from couch_named_python import UnauthorizedError
                raise UnauthorizedError("You shall not pass")
            elif new == "meh":
                {"a dict": True}["nonexistant key"]

        self.vs.okay()
        self.vs.compile("thefunction").AndReturn(f)
        self.vs.single(1)
        self.vs.log("Some sort of log")
        self.vs.single({"forbidden": "Some sort of error."})
        self.vs.single({"unauthorized": "You shall not pass"})

        self.mocker.ReplayAll()

        self.vs.add_ddoc("design", {"validate_doc_update": "thefunction"})
        self.vs.use_ddoc("design", ["validate_doc_update"], [1, 2, 3, 4])
        self.vs.use_ddoc("design", ["validate_doc_update"], ["bad", 2, 3, 4])
        self.vs.use_ddoc("design", ["validate_doc_update"], ["what", 2, 3, 4])

        try:
            self.vs.use_ddoc("design", ["validate_doc_update"],
                    ["meh", 2, 3, 4])
        except KeyError as e:
            pass
        else:
            raise Exception("Expected KeyError")

        self.mocker.VerifyAll()

    def test_filter(self):
        def f(doc, req):
            assert req["userCtx"] == 4
            n = doc["n"]
            if n == 0:
                return 0
            return n in [2, 3, 5]

        self.vs.okay()
        self.vs.compile("filterfunc").AndReturn(f)
        self.vs.output(True, [False, False, True, True, False, True])
        self.mocker.ReplayAll()

        self.vs.add_ddoc("w/hat", {"filters": {"prime": "filterfunc"}})
        self.vs.use_ddoc("w/hat", ["filters", "prime"],
                [[{"n": i} for i in xrange(6)], {"userCtx": 4}])
        self.mocker.VerifyAll()

    def test_ddoc_shows(self):
        def f(doc, req):
            assert req["value"] == 4
            if doc["case"] == 1:
                return {"body": doc["sometext"]}
            elif doc["case"] == 2:
                return {"code": 500}
            else:
                return doc["sometext"]
        def g(doc, req):
            from couch_named_python import start, send
            start({"code": 403})
            send("You can't be here\n")
            send("It's dangerous\n")
        def h(doc, req):
            from couch_named_python import NotFoundError, Redirect, send
            send("Some text")
            if doc == None:
                raise NotFoundError("Help")
            elif "nf" in doc:
                raise NotFoundError()
            elif "meh" in doc:
                raise Redirect("/somewhere_else")
            elif "wat" in doc:
                raise Redirect("/wat", permanent=True)

        self.vs.okay()

        self.vs.compile("showf").AndReturn(f)
        self.vs.output("resp", {"body": "Test text 1"})
        self.vs.output("resp", {"code": 500})
        self.vs.output("resp", {"body": "Test text 2"})

        self.vs.compile("showg").AndReturn(g)
        self.vs.output("resp", {"code": 403,
                                "body": "You can't be here\nIt's dangerous\n"})

        self.vs.compile("showh").AndReturn(h)
        self.vs.output("error", "not_found", "Help")
        self.vs.output("error", "not_found", "document not found")
        self.vs.output("resp", {"code": 302, "headers":
                            {"Location": "/somewhere_else"}})
        self.vs.output("resp", {"code": 301, "headers":
                            {"Location": "/wat"}})

        self.mocker.ReplayAll()
        self.vs.add_ddoc("desid", {"shows": {"f": "showf", "g": "showg",
                            "h": "showh"}})

        self.vs.use_ddoc("desid", ["shows", "f"], [{"case": 1,
                            "sometext": "Test text 1"}, {"value": 4}])
        self.vs.use_ddoc("desid", ["shows", "f"], [{"case": 2}, {"value": 4}])
        self.vs.use_ddoc("desid", ["shows", "f"], [{"case": 3, 
                            "sometext": "Test text 2"}, {"value": 4}])

        self.vs.use_ddoc("desid", ["shows", "g"], [{}, {}])

        self.vs.use_ddoc("desid", ["shows", "h"], [None, {}])
        self.vs.use_ddoc("desid", ["shows", "h"], [{"nf": True}, {}])
        self.vs.use_ddoc("desid", ["shows", "h"], [{"meh": True}, {}])
        self.vs.use_ddoc("desid", ["shows", "h"], [{"wat": True}, {}])

        self.mocker.VerifyAll()

    def test_reset(self):
        self.mocker.StubOutWithMock(gc, "collect")

        self.test_add_fun()
        self.mocker.ResetAll()
        assert len(self.vs.map_funcs) == 2

        self.vs.okay()
        self.mocker.ReplayAll()

        self.vs.reset({"reduce_limit": True})
        assert len(self.vs.map_funcs) == 0
        assert self.vs.query_config == {"reduce_limit": True}

        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.test_map_doc()
        self.mocker.ResetAll()

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
        self.vs.log("Ignored exception (map_runtime_error): "
            "KeyError: 'nonexistant', doc_id=d2, func_name=map_three, "
            "func_mod=couch_named_python.tests.test_pyviews")
        self.vs.output([["cow 1", 1], ["cow 2", 4], ["cow 3", 9]],
                       [[False, [4, 5, 6]], [True, [4, 5, 6]]],
                       [])
        self.vs.log("Ignored exception (map_runtime_error): "
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
        def f(keys, values, rereduce):
            assert rereduce == False
            assert keys == [["key1", "id1"], ["key2", "id2"]]
            return sum(values) + 41
        def g(k, v, r):
            if v[0] == 3:
                raise ValueError("Yeah whatever")
            else:
                return {"meh": True}

        self.vs.compile("func1").AndReturn(f)
        self.vs.compile("func2").AndReturn(g)
        self.vs.output(True, [41 + 102 + 251, {"meh": True}])
        self.vs.compile("func1").AndReturn(f)
        self.vs.compile("func2").AndReturn(g)
        self.vs.log("Ignored exception (reduce_runtime_error): "
                "ValueError: Yeah whatever, func_name=g, "
                "func_mod=couch_named_python.tests.test_pyviews")
        self.vs.output(True, [41 + 3 + 2, None])
        self.mocker.ReplayAll()

        self.vs.reduce(["func1", "func2"],
            [[["key1", "id1"], 102], [["key2", "id2"], 251]])
        self.vs.reduce(["func1", "func2"],
            [[["key1", "id1"], 3], [["key2", "id2"], 2]])
        self.mocker.VerifyAll()

    def test_rereduce(self):
        def f(keys, values, rereduce):
            assert rereduce
            return sum(values) - 1
        def g(k, v, r):
            assert r
            s = sum(v)
            assert s != 5
            return s

        self.vs.compile("func1").AndReturn(f)
        self.vs.compile("func2").AndReturn(g)
        self.vs.output(True, [11, 12])
        self.vs.compile("func1").AndReturn(f)
        self.vs.compile("func2").AndReturn(g)
        self.vs.log("Ignored exception (rereduce_runtime_error): "
                "AssertionError, func_name=g, "
                "func_mod=couch_named_python.tests.test_pyviews")
        self.vs.output(True, [4, None])
        self.mocker.ReplayAll()

        self.vs.rereduce(["func1", "func2"], [7, 5])
        self.vs.rereduce(["func1", "func2"], [-5, 10])
        self.mocker.VerifyAll()

    def test_update(self):
        def f(doc, req):
            if req == {"blah": 2}:
                assert doc == {"mydoc": True}
                doc["moo"] = "milk"
                return [doc, u"astring"]
            elif req == {"boo": True}:
                assert doc == None
                return [{"newdoc": True}, {"body": "something",
                        "headers": {"Content-Type": "garbage"}}]
            else:
                assert False

        self.vs.okay()
        self.vs.compile("func").AndReturn(f)
        self.vs.output("up", {"mydoc": True, "moo": "milk"},
                        {"body": "astring"})
        self.vs.output("up", {"newdoc": True},
            {"body": "something", "headers": {"Content-Type": "garbage"}})

        self.mocker.ReplayAll()

        self.vs.add_ddoc("desid", {"updates": {"f": "func"}})
        self.vs.use_ddoc("desid", ["updates", "f"],
                            [{"mydoc": True}, {"blah": 2}])
        self.vs.use_ddoc("desid", ["updates", "f"], [None, {"boo": True}])

        self.mocker.VerifyAll()

class TestNamedPythonViewServer(object):
    def setup(self):
        self.mocker = mox.Mox()
        self.vs = NamedPythonViewServer(None, None)
        self.mocker.StubOutWithMock(self.vs, "output")

    def teardown(self):
        self.mocker.UnsetStubs()

    def test_compile(self):
        self.mocker.ReplayAll()

        name = "couch_named_python.tests.example_mod_a"
        assert name not in sys.modules
        f = self.vs.compile(name + ".func_a")
        assert name in sys.modules

        assert f() == "test function A"

        self.mocker.VerifyAll()

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

        self.compile_sysexit("couch_named_python.tests.example_mod_b."
                             "other_function")
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

    def test_checks_version(self):
        self.vs.output("error", "compile_load",
                       "ValueError: Loaded version None did not match "
                       "expected version 2")
        self.mocker.ReplayAll()

        self.compile_sysexit("couch_named_python.tests.example_mod_b.func_a|2")
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.vs.output("error", "compile_load",
                       "ValueError: Loaded version 556 did not match "
                       "expected version None")
        self.mocker.ReplayAll()

        self.compile_sysexit("couch_named_python.tests.example_mod_b.func_c")
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.vs.output("error", "compile_load",
                       "ValueError: Loaded version 556 did not match "
                       "expected version 2")
        self.mocker.ReplayAll()

        self.compile_sysexit("couch_named_python.tests.example_mod_b.func_c|2")
        self.mocker.VerifyAll()
        self.mocker.ResetAll()

        self.mocker.ReplayAll()

        # Should succeed without output
        f = self.vs.compile("couch_named_python.tests.example_mod_b.func_b|2")
        g = self.vs.compile("couch_named_python.tests.example_mod_b."
                            "func_c|556")

        # Check that the @version decorator works, and preserves docstrings
        assert f() == 50
        assert f.__doc__ == "the second function"
        assert g("blah", aword=4) == "moo ['blah', 4]"

        self.mocker.VerifyAll()


class TestMain(object):
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
