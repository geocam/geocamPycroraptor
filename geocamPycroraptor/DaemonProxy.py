# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import os
import platform

from geocamPycroCom.Dispatcher import Dispatcher
from geocamPycroraptor import commandLineOptions
from geocamPycroraptor import anyjson as json


class DaemonProxy:
    """Example usage: p = DaemonProxy(); p.start('bc')"""
    def __init__(self, opts=None, dispatcher=None, lineHandler=None,
                 connectHandler=None, **kwargs):
        if dispatcher == None:
            dispatcher = Dispatcher(moduleName='client-%s-%d' % (platform.node(), os.getpid()))
        if opts == None:
            opts, _args = commandLineOptions.getClientOptsArgs(['pyrterm'])
        for k, v in kwargs.iteritems():
            setattr(opts, k, v)
        self._opts = opts
        self._lineHandler = lineHandler
        self._connectHandler = connectHandler
        self._dispatcher = dispatcher
        _serverLoc = opts.daemons[0].strip()
        self._conns = {}
        self._currentConn = None
        self._counter = 0
        self._responseIdToWaitFor = None
        self._opened = False
        self._lastMatchingMessage = None

    def handleLine(self, sock, line):
        if self._responseIdToWaitFor != None:
            msg = json.loads(line)
            if msg[0] == 'response' and msg[1] == self._responseIdToWaitFor:
                self._lastMatchingMessage = msg
        if self._lineHandler:
            self._lineHandler(sock, line)

    def open(self):
        if not self._opened:
            if self._opts.notificationService:
                self._dispatcher.connectToNotificationService(self._opts.notificationService,
                                                              serviceHandler=self.comHandleService)
                self._dispatcher.findServices(self._opts.notificationService)
            if self._opts.daemons:
                self._connectDaemon(self._opts.daemons[0])
            self._opened = True

    def _connectDaemon(self, endpoint):
        if not endpoint in self._conns:
            newConn = (self._dispatcher.connect
                       (endpoint,
                        connectHandler=self.comHandleConnect,
                        lineHandler=self.handleLine))
            self._conns[endpoint] = newConn
            if len(self._conns) == 1:
                self._currentConn = newConn

    def comHandleService(self, finder, serviceName, serviceEvent):
        if serviceName.startswith('pyraptord'):
            self._connectDaemon(serviceEvent)

    def comHandleConnect(self, sock):
        # asyncore should set connected flag earlier -- avoid infinite loop
        sock.connected = True
        if self._connectHandler:
            self._connectHandler(sock)

    def send(self, cmdString):
        if not (self._currentConn and self._currentConn.connected):
            self.open()

            def _check():
                if self._currentConn.connected:
                    return True
                else:
                    return None

            self._dispatcher.waitForResponse(_check)
        self._currentConn.write(cmdString + '\n')

    def sendObject(self, cmdObject):
        self.send(json.dumps(cmdObject))

    def sendCommand(self, cmd):
        self.sendObject(['command', self._counter] + cmd)
        ret = self._counter
        self._counter += 1
        return ret

    def sendStart(self, *processes):
        return self.sendCommand(['start'] + list(processes))

    def sendStop(self, *processes):
        return self.sendCommand(['stop'] + list(processes))

    def sendRestart(self, *processes):
        return self.sendCommand(['restart'] + list(processes))

    def sendGet(self, var):
        return self.sendCommand(['get', var])

    def sendSubStatus(self, *processes):
        return self.sendCommand(['sub', 'status'] + list(processes))

    def returnGetResponse(self, var):
        return self.waitForResponse(self.sendGet(var))

    def waitForResponse(self, responseId):
        self._responseIdToWaitFor = responseId
        self._lastMatchingMessage = None
        response = self._dispatcher.waitForResponse(lambda: self._lastMatchingMessage)
        self._responseIdToWaitFor = None
        return response[2:]

    def close(self):
        if self._opened:
            self._dispatcher.close()
            self._conns = {}
            self._currentConn = None
            self._opened = False
