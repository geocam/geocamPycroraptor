# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import sys
import traceback


def printTraceback(exitOnKeyboardInterrupt=True):
    errClass, errObject, errTB = sys.exc_info()[:3]
    traceback.print_tb(errTB)
    print >> sys.stderr, ('%s.%s: %s' % (errClass.__module__,
                                         errClass.__name__,
                                         str(errObject)))
    if exitOnKeyboardInterrupt and errClass is KeyboardInterrupt:
        sys.exit(0)
