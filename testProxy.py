#!/usr/bin/env python

# used this for debugging an intermittent problem with connecting
# to pyraptord over tcp.  the problem seems to be gone now but
# the tester may still be useful.

import os
from pycroraptor.DaemonProxy import DaemonProxy
from pycroraptor import commandLineOptions

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
