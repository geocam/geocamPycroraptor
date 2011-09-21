# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import sys

from geocamPycroraptor.Printable import Printable
from geocamPycroraptor.PycroEncoder import PycroEncoder
from geocamPycroraptor import anyjson as json


class Slave(Printable):
    def __init__(self, name, endpoint, dispatcher, logComm=True, statusHandler=None):
        # pylint: disable=W0231
        self.name = name
        self.endpoint = endpoint
        self.dispatcher = dispatcher
        self.logComm = logComm
        self.statusHandler = statusHandler
        self.status = None
        self.conn = None

    def connect(self):
        self.conn = self.dispatcher.connect(self.endpoint, connectHandler=self.handleConnect,
                                            lineHandler=self.handleLine)

    def isConnected(self):
        return self.conn.connected

    def write(self, text):
        if self.logComm:
            print 'Slave: write:', text,
            sys.stdout.flush()
        self.conn.write(text)

    def writeObject(self, obj):
        self.write(json.dumps(obj, cls=PycroEncoder) + '\n')

    def handleConnect(self, conn):
        self.write('sub status -a\n')
        self.write('get status -a\n')

    def handleLine(self, conn, text):
        cmd = json.loads(text)
        print 'Slave: handleLine:', cmd
        if cmd[0] == 'status':
            _, taskName, status = cmd
            self.handleStatus(taskName, status)
        else:
            pass  # nothing to do for other message types yet

    def handleStatus(self, taskName, status):
        if self.statusHandler:
            self.statusHandler(self, taskName, status)
        else:
            pass  # no default action
