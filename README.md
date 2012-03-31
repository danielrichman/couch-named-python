couch-named-python
==================

Introduction TODO

Installation
============

You will need couch-named-python and your functions installed in the same
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
for example if ``myviews.py`` (which is installed in the /opt/couch_vs python
path by pip) contained

    from couch_named_python import Unauthorized, Forbidden, version

    @version(123)
    def townmap(doc):
        yield doc["town"]

    @version(21)
    def validate(new, old, userctx, secobj):
        if userctx["name"] != "daniel":
            raise Unauthorized("No")
        elif "town" not in new:
            raise Forbidden("No town in doc")

Then the design doc might be

    {"id": "_design/location",
     "views": {"towns": {"map": "myviews.townmap|123"}},
     "validate_doc_update": "myviews.validate|21",
     "language": "python"}

i.e., the format is ``module.module.function|version``.

Rational for @version decorator
===============================

When the code is stored in the design document, like with the default
javascript view server, CouchDB can track and deal with changes.

There are a few main reasons:

 - couch-named-python doesn't reload modules. The viewserver will have to die
   by SIGTERM or error in order to force it to reload code.
 - couch-named-python can't tell CouchDB that the view function has been
   changed. CouchDB will not even think that the view function has changed
   unless you modify the string for the function in the design document
   (saving the doc without changes or modifying other attributes doesn't work).
 - It's actually quite difficult for couch-named-python to even work out if
   the view function's behaviour has changed, since it could be spread across
   more than one file.

Annotating functions with a manually changed 'version' is the easiest
solution.

When doing an upgrade, you need to:

 - update your python files, changing the @version on functions whose
   behaviour has changed
 - re-upload the design docs for these functions
 - load a view to make sure everything's back up.

If the versions on a loaded function and the design doc don't match then
the view server raises an error and dies.
This will probably cause the request that initiated the view update to fail
and instead produce an {"error": blah} response from couch. Refreshing the
page will restart the view server, load the updated file, and run the view
properly. (Alternatively, you may kill the view server process yourself.
If it's idle at the time, couch won't mind, and won't complain on first
view load.)

Use of the version decorator and checking for it is optional but strongly
recommended. You may simply use functions without the decorator and put
``module.module.function`` in the design document if you wish.
