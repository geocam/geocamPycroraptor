# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import sys
import platform
import os
from cStringIO import StringIO

from geocamPycroCom.Dispatcher import Dispatcher
from geocamPycroCom.SharedScheduler import scheduler, ExitSchedulerLoop
from geocamPycroraptor import commandLineOptions
from geocamPycroraptor.DaemonProxy import DaemonProxy
from geocamPycroraptor import anyjson as json


class Client:
    def __init__(self, opts=None):
        self._opts = opts
        self._needPrompt = True
        self._com = None
        self._proxy = None

    def _printIfInteractive(self, text):
        if self._opts.startupCommand == None:
            sys.stdout.write(text)
            sys.stdout.flush()

    def _prompt(self):
        self._printIfInteractive('pyrterm> ')

    def _queuePrompt(self):
        self._needPrompt = True
        scheduler.enterSimple(delay=0.05, action=self._checkPrompt)

    def _checkPrompt(self):
        if self._needPrompt:
            self._prompt()
            self._needPrompt = False

    def handleStdinLine(self, sock, line):
        if line == 'q' or line == 'quit':
            print 'user quit'
            raise ExitSchedulerLoop(None)
        elif line:
            self._proxy.send(line)
        else:
            self._prompt()

    def handleDaemonConnect(self, sock):
        if self._opts.startupCommand != None:
            self._proxy.send(self._opts.startupCommand)
            raise ExitSchedulerLoop(None)

    def makeStatusHumanReadable(self, result):
        statusDict = result['status']
        statusPairs = statusDict.items()
        statusPairs.sort(key=lambda pair: pair[0].lower())
        if len(statusPairs) == 1:
            return '%s' % statusPairs[0][1]
        else:
            out = StringIO()
            out.write('\n')
            for taskName, info in statusPairs:
                secondaryInfo = ['%s=%s' % (k, info[k])
                                 for k in ('pid', 'sigName', 'sigVerbose', 'returnValue')
                                 if k in info]
                out.write('  %-20s %-11s %s\n' % (taskName, info['procStatus'],
                                               ' '.join(secondaryInfo)))
            out.write('\n')
            out.write('  get status.<taskName> for more details\n')
            return out.getvalue()

    def makeOkResponseHumanReadable(self, result):
        if isinstance(result, dict) and len(result) == 1:
            if 'status' in result:
                return self.makeStatusHumanReadable(result)
            else:
                return '%s' % result.values()[0]
        else:
            if result == None:
                return 'ok'
            else:
                return 'ok %s' % result

    def makeHumanReadable(self, line):
        if line.startswith('#'):
            return line
        else:
            cmd = json.loads(line)
            if (cmd and cmd[0] == 'response'):
                _response, _lineId, returnCode = cmd[:3]
                result = cmd[3:]
                if returnCode == 'ok':
                    return self.makeOkResponseHumanReadable(result[0])
                else:
                    return ' '.join([returnCode] + result)
            else:
                return line

    def handleDaemonLine(self, sock, line):
        displayText = self.makeHumanReadable(line)
        sys.stdout.write(displayText + '\n')
        self._queuePrompt()

    def runx(self):
        self._com = Dispatcher(moduleName='client-%s-%d' % (platform.node(), os.getpid()))
        self._proxy = DaemonProxy(self._opts,
                                  dispatcher=self._com,
                                  lineHandler=self.handleDaemonLine,
                                  connectHandler=self.handleDaemonConnect)
        self._proxy.open()
        self._com.connect('console:', lineHandler=self.handleStdinLine)
        self._printIfInteractive('example commands: "start bc", "stop bc", "get status.bc"\n')
        self._prompt()
        self._com.runForever()

    @staticmethod
    def run(argv):
        opts, _args = commandLineOptions.getClientOptsArgs(argv)
        Client(opts).runx()
