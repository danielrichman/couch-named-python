# Copyright 2012 (C) Daniel Richman; GNU GPL 3

import sys
import mox
import couchdbkit
from copy import deepcopy
import __builtin__

from .. import uploader
from ..uploader import generate_doc, upload, main

mod = "couch_named_python.tests.example_mod_c"

ymlfile_a = \
"""
design_a:
    views:
        one: #.smap
        two: #.smap
design_b:
    views:
        stats:
            map: #.pmap
            reduce: #.pred
""".replace("#", mod)

ymlfile_b = \
"""
design_c:
    shows:
        whatever: #.s_one
    updates:
        u: #.u_one
    filters:
        f1: #.f_one
        f2: #.f_two
    validate_doc_update: #.validate
""".replace("#", mod)

main_docs = [{"_id": "_design/design_a", "language": "python",
              "views": {"one": {"map": mod + ".smap|5"},
                        "two": {"map": mod + ".smap|5"}}},
             {"_id": "_design/design_b", "language": "python",
              "views": {"stats": {"map": mod + ".pmap|5",
                                  "reduce": mod + ".pred|100"}}},
             {"_id": "_design/design_c", "language": "python",
              "shows": {"whatever": mod + ".s_one"},
              "updates": {"u": mod + ".u_one|5"},
              "filters": {"f1": mod + ".f_one|2", "f2": mod + ".f_two|2"},
              "validate_doc_update": mod + ".validate|100"}]


class TestUploader(object):
    def setup(self):
        self.m = mox.Mox()

    def teardown(self):
        self.m.UnsetStubs()

        if hasattr(self, 'old_argv'):
            sys.argv = self.old_argv
        if hasattr(uploader, 'open'):
            del uploader.open

    def test_creates_doc_correctly(self):
        m = lambda f: mod + "." + f
        doc = {"shows": {"show1": m("s_one"), "show2": m("s_two")},
               "lists": {"list1": m("l_one"), "list2": m("l_two")},
               "filters": {"filter1": m("f_one"), "filter2": m("f_two")},
               "updates": {"update1": m("u_one")},
               "views": {"simple_map": m("smap"),
                   "properview": {"map": m("pmap"), "reduce": m("pred")},
                   "sumreduce": {"map": m("pmap"), "reduce": "_sum"},
                   "countreduce": {"map": m("pmap"), "reduce": "_count"},
                   "statsreduce": {"map": m("pmap"), "reduce": "_stats"}},
               "validate_doc_update": m("validate")}
        expect = {"_id": "_design/mydesign", "language": "python",
               "shows": {"show1": m("s_one"), "show2": m("s_two")},
               "lists": {"list1": m("l_one"), "list2": m("l_two|2")},
               "filters": {"filter1": m("f_one|2"), "filter2": m("f_two|2")},
               "updates": {"update1": m("u_one|5")},
               "views": {"simple_map": {"map": m("smap|5")},
                  "properview": {"map": m("pmap|5"), "reduce": m("pred|100")},
                   "sumreduce": {"map": m("pmap|5"), "reduce": "_sum"},
                   "countreduce": {"map": m("pmap|5"), "reduce": "_count"},
                   "statsreduce": {"map": m("pmap|5"), "reduce": "_stats"}},
               "validate_doc_update": m("validate|100")}

        # generate_doc modifies the dict in-place
        tmp = deepcopy(doc)
        generate_doc("mydesign", tmp)
        assert tmp == expect

    def test_uploads(self):
        self.m.StubOutWithMock(uploader, 'couchdbkit')
        self.mock_server = self.m.CreateMock(couchdbkit.Server)
        self.mock_db = self.m.CreateMock(couchdbkit.Database)
        uploader.couchdbkit.Server("http://server:port")\
                .AndReturn(self.mock_server)
        self.mock_server.__getitem__("database").AndReturn(self.mock_db)

        docs = [{"_id": "design/one"}, {"_id": "design/two"}]
        self.mock_db.save_doc(docs[0], force_update=True)
        self.mock_db.save_doc(docs[1], force_update=True)

        self.m.ReplayAll()
        upload("http://server:port", "database", docs)
        self.m.VerifyAll()

    def test_main(self):
        # such that with open('file') as f: leaves f as a string
        class F(object):
            def __init__(self, s):
                self.s = s
            def __enter__(self):
                return self.s
            def __exit__(self, *args):
                pass
        def f(x):
            if x == "file1.yml":
                return F(ymlfile_a)
            elif x == "file2.yml":
                return F(ymlfile_b)
            else:
                assert False

        uploader.open = f
        self.old_argv = sys.argv

        assert hasattr(uploader, 'open')
        assert hasattr(self, 'old_argv')

        sys.argv = ["prog", "http://server:5984", "database2",
                    "file1.yml", "file2.yml"]

        self.m.StubOutWithMock(uploader, 'couchdbkit')
        self.mock_server = self.m.CreateMock(couchdbkit.Server)
        self.mock_db = self.m.CreateMock(couchdbkit.Database)
        uploader.couchdbkit.Server("http://server:5984")\
                .AndReturn(self.mock_server)
        self.mock_server.__getitem__("database2").AndReturn(self.mock_db)

        self.mock_db.save_doc(main_docs[0], force_update=True).InAnyOrder()
        self.mock_db.save_doc(main_docs[1], force_update=True).InAnyOrder()
        self.mock_db.save_doc(main_docs[2], force_update=True).InAnyOrder()

        self.m.ReplayAll()

        main()

        self.m.VerifyAll()
