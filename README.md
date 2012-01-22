couch-named-python
==================

Introduction TODO

Installation
============

You will need couch-named python and your functions installed in the same
python path, be it globally, in a virtualenv, or a distribute-less folder with
a wrapper script that sets the pythonpath and then invokes
``couch_named_python.pyviews:main``. In this example I'm using virtualenv:

    virtualenv /opt/couch_vs
    source /opt/couch_vs/bin/activate
    pip install couch-named-python myfunctions
    # or check out each package, and use ./setup.py install while virtualenv'd.

Next, edit /etc/couchdb/local.ini and add to the query_servers section:

    [query_servers]
    python = /opt/couch_vs/bin/couch-named-python

And restart couchdb

Usage
=====

Functions in the design doc are just module.module.module.function paths,
for example if ``/opt/couch_vs/lib/python2.?/myviews.py`` contained

    from couch_named_python import Unauthorized, Forbidden

    def townmap(doc):
        yield doc["town"]

    def validate(new, old, userctx, secobj):
        if userctx["name"] != "daniel":
            raise Unauthorized("No")
        elif "town" not in new:
            raise Forbidden("No town in doc")

Then the design doc might be

    {"id": "_design/location",
     "views": {"towns": {"map": "myviews.townmap"}},
     "validate_doc_update": "myviews.validate"}

Note that couch-named-python doesn't reload() modules, so if you change
something you'll need to give it a kick by killing the viewserver process
or restarting couch.
