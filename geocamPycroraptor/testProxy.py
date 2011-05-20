#!/usr/bin/env python
# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

# used this for debugging an intermittent problem with connecting
# to pyraptord over tcp.  the problem seems to be gone now but
# the tester may still be useful.

import os
from geocamPycroraptor.DaemonProxy import DaemonProxy
from geocamPycroraptor import commandLineOptions

def handleLine(sock, line):
    print 'testProxy: line =', line

pyraptordProxy = DaemonProxy(lineHandler=handleLine)

def waitOnce():
    print 'testProxy: sending get status'
    retCode, namespace = pyraptordProxy.returnGetResponse('status')
    taskStatus = namespace['status']
    print 'testProxy: status =', taskStatus
    pyraptordProxy.close()
    print 'testProxy: closed'

for i in xrange(0,3):
    waitOnce()
