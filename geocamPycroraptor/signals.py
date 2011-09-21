# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import signal

SIG_VERBOSE_CONFIG = [('HUP', 'hangup; e.g. tty was closed, unusual under pyraptord'),
                      ('INT', 'interrupt; e.g. a Ctrl-C'),
                      ('ILL', 'illegal instruction; e.g. corrupted binary'),
                      ('ABRT', 'abort; e.g. failed assertion or uncaught exception'),
                      ('BUS', 'bus error; e.g. array out of bounds'),
                      ('KILL', 'kill; e.g. pyraptord stop second attempt'),
                      ('SEGV', 'segmentation fault; e.g. dereferenced null pointer'),
                      ('PIPE', 'broken pipe; e.g. lost network connection'),
                      ('TERM', 'terminate; e.g. pyraptord stop'),
                      ]

SIG_VERBOSE = {}
for name, verbose in SIG_VERBOSE_CONFIG:
    try:
        sigNum = getattr(signal, 'SIG' + name)
    except AttributeError:
        continue  # doh, can't look up number for signal name on this platform
    SIG_VERBOSE[sigNum] = dict(sigName=name, sigVerbose=verbose)
