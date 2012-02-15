#!/usr/bin/env python
from distutils.core import setup

setup(
    name="couch-named-python",
    version="0.1.2dev",
    author="Daniel Richman",
    author_email="main@danielrichman.co.uk",
    url="https://github.com/danielrichman/couch-named-python",
    description="CouchDB view server that executes functions "
                "on the python path by name",
    packages=["couch_named_python"],
    tests_require=["mox>=0.5"],
    license="GNU General Public License Version 3",
    entry_points = {
        "console_scripts": [
            "couch-named-python = couch_named_python.pyviews:main"
        ]
    }
)
