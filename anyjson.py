# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

"""
A wrapper module that tries multiple methods of importing JSON
support.  Recommended usage:

from geocamPycroraptor import anyjson as json
"""

try:
    # user explicitly installed some version of json module,
    # prefer their version
    from simplejson import *
except ImportError:
    try:
        # C-compiled json included by default in Python 2.6+
        from json import *
    except ImportError:
        # backstop, Django ships with a (slower) pure-Python json
        from django.utils.simplejson import *
