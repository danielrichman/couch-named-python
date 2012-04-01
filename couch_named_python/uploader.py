# Copyright 2011 (C) Daniel Richman; GNU GPL 3

"""
The design doc uploader takes a yml file, like the example below,
and produces a design doc and uploads it to the specified CouchDB server.
This should make keeping your design docs neatly stored a lot easier.

Example:

    farm:
        views:
            sheep: my_module.farm.sheep_view
            goat_sizes:
                map: my_module.farm.goat_size
                reduce: my_module.farm.goat_size_reduce

        validate_doc_update: my_module.validate

        shows:
            blah: my_module.whatever.blah

    barn:
        validate_doc_update: my_module.something_else

        views:
            another_view: my_module.small_function

Running the uploader on this would produce _design/farm and _design/barn.
You do not need to specify the |version suffixes on your function names,
the uploader will import the modules and append them.
"""

import sys
import yaml
import optparse
import couchdbkit

from . import get_version

def append_version(function):
    assert '|' not in function

    parts = function.split(".")
    if len(parts) < 2 or "" in parts:
        raise ValueError("Invalid function path")
    module = '.'.join(parts[:-1])
    name = parts[-1]

    __import__(module)
    f = getattr(sys.modules[module], name)
    f_ver = get_version(f)

    if f_ver != None:
        suffix = '|' + str(f_ver)
    else:
        suffix = ''

    return function + suffix

def generate_doc(name, doc, view_server="python"):
    """
    Prepares a loaded design doc for upload

     - appends versions to function names
     - transforms short-hand map-only views

    This function modifies the design doc in place.
    """

    for func_type in ["shows", "lists", "filters", "updates"]:
        if func_type in doc:
            section = doc[func_type]
            for key in section:
                section[key] = append_version(section[key])

    if "validate_doc_update" in doc:
        doc["validate_doc_update"] = append_version(doc["validate_doc_update"])

    if "views" in doc:
        views = doc["views"]
        for key in views:
            view = views[key]

            if isinstance(view, basestring):
                views[key] = {"map": view}
                view = views[key]

            if "map" in view:
                view["map"] = append_version(view["map"])
            if "reduce" in view:
                view["reduce"] = append_version(view["reduce"])

            u = set(view) - set(["map", "reduce"])
            if u:
                print "Warning: encountered unexpected keys in a view:"
                print "    " + ' '.join(u)

    u = set(doc) - set(["shows", "lists", "filters", "updates",
                        "validate_doc_update", "views"])
    if u:
        print "Warning: encountered unexpected keys in a design doc:"
        print "    " + ' '.join(u)

    doc["_id"] = "_design/" + name
    doc["language"] = view_server

def upload(server, db, docs):
    server = couchdbkit.Server(server)
    db = server[db]

    for doc in docs:
        db.save_doc(doc, force_update=True)

oparser = optparse.OptionParser(usage="%prog [options] design.yml")
oparser.add_option("--view-server", dest="view_server", default="python",
                   metavar="VS",
                   help="The name by which couch knows the view server")

def main():
    (options, args) = oparser.parse_args()
    if len(args) < 3:
        oparser.error("You must specify the server, database, and at least "
                      "one design doc file")

    server = args[0]
    db = args[1]
    filelist = args[2:]

    docs = []

    for filename in filelist:
        with open(filename) as f:
            data = yaml.load(f)

        for name in data:
            generate_doc(name, data[name], options.view_server)
            docs.append(data[name])

    upload(server, db, docs)
