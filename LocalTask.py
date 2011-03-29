
import os
import sys
import subprocess
import time
import pty
import signal
import re
import shlex
import errno

from geocamPycroCom.SharedScheduler import scheduler

from geocamPycroraptor.ExpandVariables import expandVal
from geocamPycroraptor import Log
from geocamPycroraptor.Stdout import Stdout
from geocamPycroraptor.signals import SIG_VERBOSE
from geocamPycroraptor.BaseTask import BaseTask
from geocamPycroraptor import anyjson as json

class LocalTask(BaseTask):
    def __init__(self, name, parent):
        super(LocalTask, self).__init__(name, parent)
        self.status = dict(status = 'notStarted', procStatus = 'notStarted', params = {})
        self._proc = None
        self._pendingRestart = False
        self._doomsday = None
        self._childStdout = None
        self._env['name'] = self.name
        self._outLogger = None
        self._errLogger = None
        self._tslineLogger = None

    def setStatus(self, status):
        super(LocalTask, self).setStatus(status)
        self._logText(['status', self.name, status])

    def isLocal(self):
        return True

    def _expandWithPid(self, val):
        if self._proc:
            self._env['pid'] = self._proc.pid
        else:
            if 'pid' in self._env:
                del self._env['pid']
        return expandVal(val, self._env)

    def _getConfig(self, field):
        return self._expandWithPid(self._env[field])

    def _logText(self, obj):
        if self._tslineLogger:
            self._tslineLogger.handleLine(Log.TimestampLine('pyr', 'n', json.dumps(obj)))

    def _runCmd(self, cmd):
        print 'runCmd: %s' % cmd
        cmdArgs = shlex.split(cmd)
        devNull = file('/dev/null', 'r')
        child = subprocess.Popen(cmdArgs,
                                 stdin = devNull,
                                 stdout = subprocess.PIPE,
                                 stderr = subprocess.STDOUT,
                                 close_fds = True)
        stdout = child.communicate()
        if child.returncode != 0:
            argsString = ['"%s"' % arg for arg in cmdArgs]
            raise Exception('LocalTask._runCmd: could not execute %s' % argsString)
        return stdout

    def _checkForPendingRestart(self):
        if not self._proc and self._pendingRestart:
            self.start(self._pendingRestartParams, restart=1)
            self._pendingRestart = False
            self._pendingRestartParams = None

    def _checkForDoomsday(self):
        if self._proc and self._doomsday and time.time() > self._doomsday:
            stopBackupCmd = self._getConfig('stopBackupCmd')
            self._logText(['stopBackup', dict(source = 'unknown',
                                              cmd = shlex.split(stopBackupCmd))])
            self._runCmd(stopBackupCmd)
            self._doomsday = None

    def _postExitCleanup(self):
        self._proc = None
        self._doomsday = None
        if self._childStdout:
            self._childStdout.close()
            self._childStdout = None
        if self._logFile:
            self._logFile.close()
            self._logFile = None
        self._outLogger = None
        self._errLogger = None
        self._tslineLogger = None
        # note: keep self._logBuffer around in case a client requests old log data.
        #  it will be reinitialized the next time the task is started.
        self._checkForPendingRestart()

    def _checkForExit(self):
        if self._proc and self._proc.poll() != None:
            if self._proc.returncode < 0:
                sigNum = -self._proc.returncode
                if sigNum in (signal.SIGTERM, signal.SIGHUP):
                    status0 = 'aborted'
                else:
                    status0 = 'failed'
                newStatus = dict(status = status0,
                                 procStatus = 'signalExit',
                                 sigNum = sigNum,
                                 params = self._params)
                if sigNum in SIG_VERBOSE:
                    newStatus.update(SIG_VERBOSE[sigNum])
            elif self._proc.returncode > 0:
                newStatus = dict(status = 'failed',
                                 procStatus = 'errorExit',
                                 returnValue = self._proc.returncode,
                                 params = self._params)
            else:
                newStatus = dict(status = 'success',
                                 procStatus = 'cleanExit',
                                 returnValue = 0,
                                 params = self._params)
            self.setStatus(newStatus)
            self._postExitCleanup()

    def _openpty(self):
        try:
            readFd, writeFd = pty.openpty()
        except:
            print >>sys.stderr, 'WARNING: pty.openpty() failed, falling back to os.pipe(), may affect output buffering'
            readFd, writeFd = os.pipe()
        return readFd, writeFd

    ######################################################################
    # functions to be called from client
    ######################################################################

    def start0(self, params={}, restart=0):
        self._params = params
        for k, v in params.iteritems():
            self._env[k] = v # may want to remove these later

        cmdArgs = shlex.split(self._getConfig('cmd'))
        self._logBuffer = Log.LineBuffer()
        if self._env['log'] == None:
            self._logFile = None
        else:
            logFileName, self._logFile = Log.openLogFromTemplate(self._env['log'], self._env)
            self._tslineLogger = Log.TimestampLineLogger(self._logFile)
            self._logBuffer.addLineHandler(self._tslineLogger.handleLine)
        self._outLogger = Log.TimestampLineParser('out', self._logBuffer.handleLine)
        self._errLogger = Log.TimestampLineParser('err', self._logBuffer.handleLine)
        os.chdir(self._getConfig('workingDir'))
        childStdoutReadFd, childStdoutWriteFd = self._openpty()
        self._childStdout = Stdout(childStdoutReadFd, self._outLogger, self, 'stdout')
        childStderrReadFd, childStderrWriteFd = self._openpty()
        self._childStderr = Stdout(childStderrReadFd, self._errLogger, self, 'stderr')
        childEnv = os.environ.copy()
        for k, v in self._getConfig('env').iteritems():
            if v == None:
                if childEnv.has_key(k):
                    del childEnv[k]
            else:
                childEnv[k] = v
        if restart:
            logName = 'restart.start'
        else:
            logName = 'start'
        self._logText([logName, dict(source = 'unknown',
                                     cmd = cmdArgs)])
        try:
            self._proc = subprocess.Popen(cmdArgs,
                                          stdin = subprocess.PIPE,
                                          stdout = childStdoutWriteFd,
                                          stderr = childStderrWriteFd,
                                          env = childEnv,
                                          close_fds = True)
        except OSError, oe:
            if oe.errno == errno.ENOENT:
                startupError = "is executable '%s' in PATH? Popen call returned no such file or directory" % cmdArgs[0]
        except Error, exc:
            startupError = str(exc)
        else:
            startupError = None
        os.close(childStdoutWriteFd)
        os.close(childStderrWriteFd)
        if startupError:
            self._logText(['startupError', startupError])
            self.setStatus(dict(status='failed',
                                procStatus='errorExit',
                                returnValue=1,
                                startupFailed=1,
                                params=self._params))
            self._postExitCleanup()
        else:
            self.stdin = self._proc.stdin
            self.setStatus(dict(status = 'running',
                                procStatus = 'running',
                                pid = self._proc.pid,
                                params = self._params))

    def stop0(self, restart=0):
        stopCmd = self._getConfig('stopCmd')
        if restart:
            logName = 'restart.stop'
        else:
            logName = 'stop'
        self._logText([logName, dict(source = 'unknown',
                                     cmd = shlex.split(stopCmd))])
        self._runCmd(stopCmd)
        self._doomsday = time.time() + self._getConfig('stopBackupDelay')

    def restart(self, params={}):
        statusWas = 'was' + self.status['status'].capitalize()
        if statusWas == 'wasRunning':
            self.stop0(restart=1)
            self._pendingRestart = True
            self._pendingRestartParams = params
        else:
            self.start0(params, restart=1)
        return statusWas

    def getStatus(self):
        return self.status

    def writeStdin(self, text):
        self._logText(['stdin', dict(source = 'unknown',
                                     text = text)])
        self.stdin.write(text+'\n')
        self.stdin.flush()

    ######################################################################
    # functions to be called from parent daemon level
    ######################################################################

    def cleanup(self):
        self._checkForExit()
        self._checkForDoomsday()
        
        
