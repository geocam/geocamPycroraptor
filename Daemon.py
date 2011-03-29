
import imp
import sys
import traceback
import os
import time
import signal
import errno
import re

from geocamPycroCom.SharedScheduler import scheduler

from geocamPycroraptor.ConfigDict import ConfigDict
from geocamPycroraptor.LocalTask import LocalTask
from geocamPycroraptor.RemoteTask import RemoteTask
from geocamPycroraptor import ExpandVariables
from geocamPycroraptor import Log, commandLineOptions
import geocamPycroraptor.exceptions
from geocamPycroraptor import settings
from geocamPycroraptor.shellJson import parseShellJson
from geocamPycroraptor.signals import SIG_VERBOSE
from geocamPycroraptor.PycroEncoder import StatusGetter, PycroEncoder
from geocamPycroraptor.Slave import Slave
from geocamPycroraptor import anyjson as json

CLEANUP_PERIOD = 0.2
WRITE_STATUS_PERIOD = 5.0

class Request:
    def copy(self):
        ret = Request()
        for k, v in vars(self).iteritems():
            setattr(ret, k, v)
        return ret

class Identifier:
    def __init__(self, name):
        self.name = name

class Daemon:
    def __init__(self, opts):
        self._dotCounter = 0
        self._opts = opts
        self._localSettings, sharedSettings = ExpandVariables.splitSettings(settings)
        sharedSettings._writable = True # mark as *not* an immutable object
        self._env = dict(settings = sharedSettings,
                         status = StatusGetter(self))
        if not 'groups' in self._env['settings']:
            self._env['settings']['groups'] = ConfigDict()
        self._shuttingDown = False
        signal.signal(signal.SIGHUP, self.handleSignal)
        signal.signal(signal.SIGTERM, self.handleSignal)
        if not self._opts.foreground:
            signal.signal(signal.SIGINT, self.handleSignal)
        self._slaves = {}
        
    def handleSignal(self, sigNum, frame):
        if sigNum in SIG_VERBOSE:
            desc = SIG_VERBOSE[sigNum]['sigName']
        else:
            desc = 'unknown'
        print >>sys.stderr, 'caught signal %d (%s), shutting down' % (sigNum, desc)
        try:
            self.shutdown()
        except Exception, err:
            print >>sys.stderr, 'caught exception during shutdown!'
            errClass, errObj, errTB = sys.exc_info()[:3]
            traceback.print_tb(errTB)
            print >>sys.stderr, '%s.%s: %s' % (errClass.__module__,
                                               errClass.__name__,
                                               str(errObj))
            print >>sys.stderr, 'now doing a hard exit'
            os._exit(-1)

    def shutdown(self):
        if self._shuttingDown:
            return
        else:
            self._shuttingDown = True
            if self.getNumRunningTasks():
                print >>sys.stderr, 'stopping all tasks'
                for task in self.iterTasks():
                    if self.isLocalTask(task.name):
                        task.stop()
            else:
                print >>sys.stderr, 'no running tasks'
            self.cleanupChildren()

    def getTaskType(self, taskName):
        allTasks = self._env['settings']['tasks']
        if taskName not in allTasks:
            return 'unknownTask'
        else:
            taskConfig = allTasks[taskName]
            if 'host' in taskConfig and taskConfig['host'] != self._opts.name:
                host = taskConfig['host']
                if host in self._slaves and self._slaves[host].isConnected():
                    return 'remote'
                else:
                    return 'unknownDaemon'
            else:
                return 'local'

    def getTaskSlave(self, taskName):
        host = self._env['settings']['tasks'][taskName]['host']
        return self._slaves[host]

    def isTask(self, taskName):
        return self.getTaskType(taskName) not in ('unknownTask', 'unknownDaemon')

    def isGroup(self, groupName):
        return groupName in self._env['settings']['groups']

    def isLocalTask(self, taskName):
        return self.getTaskType(taskName) == 'local'

    def makeTask(self, taskName):
        if self.isLocalTask(taskName):
            return LocalTask(taskName, self)
        else:
            return RemoteTask(taskName, self, self.getTaskSlave(taskName))

    def getTask(self, taskName):
        if self.isTask(taskName):
            if taskName not in self._tasks:
                newTask = self.makeTask(taskName)
                if newTask is not None:
                    self._tasks[taskName] = newTask
            return self._tasks[taskName]
        else:
            raise geocamPycroraptor.exceptions.UnknownTask(taskName)

    def expandGroup1(self, taskOrGroup, tabuList=[]):
        if taskOrGroup in tabuList:
            raise geocamPycroraptor.exceptions.GroupContainsItself(taskOrGroup)
        elif self.isGroup(taskOrGroup):
            return True, self._env['settings']['groups'][taskOrGroup]
        elif (self.isTask(taskOrGroup)
              or isinstance(taskOrGroup, (int, float))):
            return False, [taskOrGroup]
        else:
            raise geocamPycroraptor.exceptions.UnknownTask(taskOrGroup)

    def expandGroup(self, taskOrGroup, tabuList=[]):
        isExpanded, expansionResult = self.expandGroup1(taskOrGroup, tabuList)
        if isExpanded:
            return self.expandGroups(expansionResult, tabuList + [taskOrGroup])
        else:
            return expansionResult

    def expandGroups(self, taskOrGroupList, tabuList=[]):
        return sum([self.expandGroup(t, tabuList) for t in taskOrGroupList], [])

    def getAllValidTasks(self):
        return [taskName
                for taskName in self._env['settings']['tasks'].keys()
                if self.isTask(taskName)]

    def getTasks(self, taskOrGroupList):
        if taskOrGroupList == ['-a']:
            #return self._tasks.asDict().values()
            #allTaskNames = self._env['settings']['tasks'].keys()
            allTaskNames = self.getAllValidTasks()
        else:
            allTaskNames = self.expandGroups(taskOrGroupList)
        return [self.getTask(n) for n in allTaskNames]

    def getTasksForRequest(self, req):
        return self.getTasks(req.args[1:])

    def dispatchCommand(self, req):
        cmd = req.args[0]
        daemonLevelName = 'command_%s' % cmd
        if hasattr(self, daemonLevelName):
            daemonLevelHandler = getattr(self, daemonLevelName)
            return daemonLevelHandler(req)
        else:
            raise geocamPycroraptor.exceptions.UnknownCommand('unknown command "%s"' % cmd)

    def dispatchCommandParse(self, conn, cmd):
        args = parseShellJson(cmd)
        print 'dispatchCommandParse args=', args
        req = Request()
        req.conn = conn
        if args[0] == 'command':
            req.id = args[1]
            req.args = args[2:]
        else:
            req.id = None
            req.args = args
        return req, self.dispatchCommand(req)

    def dispatchCommandHandleExceptions(self, conn, cmd):
        try:
            req, retVal = self.dispatchCommandParse(conn, cmd)
            return req, ['ok', retVal]
        except:
            errClass, errObject, errTB = sys.exc_info()[:3]
            traceback.print_tb(errTB)
            print >>sys.stderr, ('%s.%s: %s' % (errClass.__module__,
                                                errClass.__name__,
                                                str(errObject)))
            if isinstance(errObject, geocamPycroraptor.exceptions.PycroWarning):
                errLevel = 'warning'
            else:
                errLevel = 'error'
            result = [errLevel,
                      '%s.%s' % (errClass.__module__, errClass.__name__),
                      str(errObject)]
            #print 'result0:', result
            return None, result

    def evalObject(self, val):
        if isinstance(val, (str, unicode)):
            if (val.startswith('"')
                or val.startswith("'")):
                # quoted string, strip quotes
                return val[1:-1]
            else:
                # bareword, do var lookup
                return ExpandVariables.getVariable(val, self._env)
        else:
            return val

    def command_start(self, req):
        if self._shuttingDown:
            raise geocamPycroraptor.exceptions.InvalidCommand("can't run tasks during shutdown")
        taskArgs = req.args[1:]
        if taskArgs and isinstance(taskArgs[-1], dict):
            params = taskArgs.pop(-1)
        else:
            params = {}
        tasks = self.getTasks(taskArgs)
        numStarted = 0
        for task in tasks:
            numStarted += task.start(params)
        if numStarted == 0:
            if len(tasks) == 0:
                msg = 'no tasks, nothing to start'
            elif len(tasks) == 1:
                msg = 'task %s already running' % tasks[0].name
            else:
                msg = 'all tasks already running'
            raise geocamPycroraptor.exceptions.NothingToDo(msg)

    def command_run(self, req):
        """run is an alias for start"""
        return self.command_start(req)

    def command_restart(self, req):
        for task in self.getTasksForRequest(req):
            task.restart()
        return None

    def command_stop(self, req):
        tasks = self.getTasksForRequest(req)
        numStopped = 0
        for task in tasks:
            numStopped += task.stop()
        if numStopped == 0:
            if len(tasks) == 0:
                msg = 'no tasks, nothing to stop'
            elif len(tasks) == 1:
                msg = 'task %s not running' % tasks[0].name
            else:
                msg = 'all tasks already stopped'
            raise geocamPycroraptor.exceptions.NothingToDo(msg)

    def command_kill(self, req):
        """kill is an alias for stop"""
        return self.command_stop(req)

    def commandGetStatus(self, req):
        taskNames = req.args[2:]
        tasks = self.getTasks(taskNames)
        for task in tasks:
            status = task.getStatus()
            if status is not None:
                self.writeObject(req.conn, ['status', task.name, status])
        return None

    def command_get(self, req):
        if req.args[1] == 'status' and len(req.args) > 2:
            # new style
            return self.commandGetStatus(req)
        else:
            # old style
            return dict(((k, ExpandVariables.getVariable(k, self._env))
                         for k in req.args[1:]))

    def command_set(self, req):
        key = req.args[1]
        val = self.evalObject(req.args[2])
        ExpandVariables.setVariable(key, val, self._env)

    def command_update(self, req):
        key = req.args[1]
        updateDict = self.evalObject(req.args[2])
        ExpandVariables.updateVariable(key, updateDict, self._env)

    def command_del(self, req):
        for key in req.args[1:]:
            ExpandVariables.delVariable(key, self._env)

    def command_stdin(self, req):
        taskName, quotedText = req.args[1:]
        if not (isinstance(quotedText, (str, unicode)) and re.match('".*"', quotedText)):
            raise geocamPycroraptor.exceptions.SyntaxError('<text> arg to stdin command must be a quoted string; instead got: %s' % quotedText)
        text = quotedText[1:-1]
        self.getTask(taskName).writeStdin(text)

    def command_help(self, req):
        req.conn.write("""#
# pyraptord commands:
#
# start/run <task1> .. [params] Start tasks (-a for all)
# stop/kill <task1> ..          Stop tasks (-a for all)
# restart <task1> ..            Restart tasks (-a for all)
#
# get <var1> ..                 Return value of vars
# set <var> <value>             Set value of var
# del <var1> ..                 Delete vars
# update <var> <valuesDict>     Set multiple attributes of var
#
# stdin <task> <text>           Write text to task stdin
#
# pyraptord variables:
#
# settings                      All settings
# settings.tasks.<task>         Persistent settings for task
# status.<task>                 Status of task
# console.<task>                Console output of task (stdout and stderr)
#
""")
        return None
        
    def commandSubStatus(self, req):
        tasks = self.getTasks(req.args[2:])
        for task in tasks:
            task._statusSubscribers.add(req.conn)
        return None

    def command_sub(self, req):
        if req.args[1] == 'status':
            return self.commandSubStatus(req)
        else:
            raise geocamPycroraptor.exceptions.SyntaxError('expected "status" after "sub"')

    def commandUnsubStatus(self, req):
        tasks = self.getTasks(req.args[2:])
        for task in tasks:
            task._statusSubscribers.remove(req.conn)
        return None

    def command_unsub(self, req):
        if req.args[1] == 'status':
            return self.commandUnsubStatus(req)
        else:
            raise geocamPycroraptor.exceptions.SyntaxError('expected "status" after "unsub"')

    def commandHandler(self, conn, cmd):
        if self._opts.logComm:
            print 'command:', repr(cmd)
        req, returnVal = self.dispatchCommandHandleExceptions(conn, cmd)
        if req == None:
            responseId = None
        else:
            responseId = req.id
        response = ["response", responseId] + returnVal
        jsonResponse = json.dumps(response, cls=PycroEncoder)
        if self._opts.logComm:
            print 'response:', jsonResponse
        conn.write(jsonResponse + '\n')
    
    def writeObject(self, conn, obj):
        conn.write(json.dumps(obj, cls=PycroEncoder) + '\n')

    def iterTasks(self):
        return self._tasks.asDict().itervalues()

    def getNumRunningTasks(self):
        return sum((task.isRunning() for task in self.iterTasks()))

    def cleanupChildren(self):
        for task in self.iterTasks():
            task.cleanup()
        if self._shuttingDown:
            if self.getNumRunningTasks() == 0:
                self.finishShutdown()

    def finishShutdown(self):
        print >>sys.stderr, 'all tasks stopped, exiting'
        os._exit(0) # sys.exit would be caught in SharedScheduler

    def daemonize(self, logNameTemplate, pidFileName):
        os.chdir('/')
        os.umask(0)

        # close stdin
        devNull = file('/dev/null', 'rw')
        os.dup2(devNull.fileno(), 0)

        # redirect stdout and stderr to log file
        if logNameTemplate == None:
            logFile = devNull
        else:
            logName, logFile = Log.openLogFromTemplate(logNameTemplate, self._env['settings'])
        print 'starting pyraptord -- log file %s' % logName
        os.dup2(logFile.fileno(), 1)
        os.dup2(logFile.fileno(), 2)
        sys.stdout = Log.StreamLogger('out', sys.stdout)
        sys.stderr = Log.StreamLogger('err', sys.stderr)

        # detach from tty
        pid = os.fork()
        if pid:
            os._exit(0)
        os.setsid()
        pid = os.fork()
        if pid:
            os._exit(0)

        # write pid file
        if pidFileName != None:
            pidDir = os.path.dirname(pidFileName)
            if not os.path.isdir(pidDir):
                os.makedirs(pidDir)
            pidFile = file(pidFileName, 'w')
            pidFile.write('%d\n' % os.getpid())
            pidFile.close()

    def handleSlaveStatus(self, slave, taskName, status):
        self.getTask(taskName).setStatus(status)

    def getStatus(self):
        pidFileName = self._opts.pidFile
        if os.path.isfile(pidFileName):
            pid = int(file(pidFileName, 'r').read())
            return (pid, 'pyraptord appears to be running with pid %d -- pid file %s' % (pid, pidFileName))
        else:
            return (0, 'pyraptord does not appear to be running -- pid file %s' % pidFileName)

    def comConnectHandler(self, sock):
        if self._opts.logComm:
            print 'connected to client on geocamPycroCom endpoint "%s"' % sock.endpoint
        self.writeObject(sock, ['name', self._dispatcher._moduleName])

    def getStatusUrl(self, taskName):
        taskConfig = self._env['settings']['tasks'][taskName]
        if ('host' in taskConfig and taskConfig['host'] != self._opts.name):
            if taskConfig['host'] in settings.REMOTE_STATUS_URLS:
                return settings.REMOTE_STATUS_URLS[taskConfig['host']] + '/'
            else:
                return 'put_%s_in_REMOTE_STATUS_URLS/' % taskConfig['host']
        else:
            return ''

    def writeStatus(self):
        sfile = Log.openLogFromFileName('%s.tmp' % self._opts.statusFile, 'w')
        title = 'Pycroraptor'
        sfile.write("""
<html>
  <head>
    <title>%s</title>
    <style type="text/css">
      body { font-family: sans-serif; }
      td { padding: 2px; }
    </style>
  </head>
  <body>
    <b>%s</b> <a href="logs/pyraptord_latest.txt">master log file</a><br/>
"""
                       % (title, title))
        statusDict = self._env['status'].asDict()
        if statusDict:
            sfile.write('<table>\n')
            sfile.write("""
<tr>
  <td><i>task</i></td>
  <td><i>status</i></td>
  <td><i>details</i></td>
</tr>
""")
            statusPairs = statusDict.items()
            statusPairs.sort()
            for name, info in statusPairs:
                if info is None:
                    continue
                procStatus = info['procStatus']
                details = ' '.join(['%s=%s' % (k, info[k])
                                    for k in ('pid', 'sigName', 'sigVerbose', 'returnValue')
                                    if info.has_key(k)])

                if procStatus == 'errorExit':
                    color = 'red'
                elif procStatus == 'signalExit' and info['sigName'] not in ('TERM', 'INT'):
                    color = 'red'
                elif procStatus == 'running':
                    color = 'green'
                else:
                    color = 'black'

                if color == 'black':
                    colorTemplate = '<font color="black">%s</font>'
                else:
                    colorTemplate = '<font color="%s"><b>%%s</b></font>' % color

                nameBlock = colorTemplate % name
                statusBlock = colorTemplate % procStatus
                detailsBlock = colorTemplate % details

                statusUrl = self.getStatusUrl(name)
                sfile.write("""
<tr>
  <td><a href="%slogs/%s_latest.txt">%s</a></td>
  <td><a href="%slogs/%s_latest.txt" style="text-decoration: none;">%s</a></td>
  <td><a href="%slogs/%s_latest.txt" style="text-decoration: none;">%s</a></td>
</tr>
""" % (statusUrl, name, nameBlock, statusUrl, name, statusBlock, statusUrl, name, detailsBlock))
            sfile.write('</table>')
        else:
            sfile.write('<p>[no tasks]</p>')
        sfile.write("""
<p>
  Last updated: %s
</p>
"""
                       % (time.strftime('%Y/%m/%d %H:%M:%S'),))
        sfile.write('</body></html>\n')
        sfile.close()
        # atomic write should avoid browser getting truncated file
        os.rename('%s.tmp' % self._opts.statusFile,
                  self._opts.statusFile)

    def start(self):
        logNameTemplate = self._opts.logFile
        if not self._opts.foreground:
            self.daemonize(logNameTemplate = logNameTemplate,
                           pidFileName = self._opts.pidFile)

        print ('\n\n--- pyraptord started at %s, pid %d ---\n'
               % (time.ctime(), os.getpid()))

        self._tasks = ConfigDict({})

        if self._opts.startupGroup.lower() not in ('', 'none'):
            print 'running tasks in startup group "%s"' % self._opts.startupGroup
            try:
                startupTasks = self.expandGroup(self._opts.startupGroup)
            except geocamPycroraptor.exceptions.UnknownTask, err:
                print >>sys.stderr, ('could not run startup group "%s": %s'
                                     % (self._opts.startupGroup, err))
            else:
                print 'startup tasks are: %s' % str(startupTasks)
                for taskName in startupTasks:
                    if isinstance(taskName, (float, int)):
                        # HACK.  if a number is in the list, delay that
                        # number of seconds.
                        print 'startup: sleeping for %f seconds' % taskName
                        time.sleep(taskName)
                    else:
                        print 'startup: starting %s' % taskName
                        self.getTask(taskName).start()
        else:
            print '[there is no startup group]'

        # initialize geocamPycroCom
        from geocamPycroCom.Dispatcher import Dispatcher
        moduleName = 'pyraptord-%s-%d' % (self._opts.name, os.getpid())
        self._dispatcher = Dispatcher(moduleName=moduleName)

        # connect to slave daemons
        if hasattr(settings, 'SLAVE_DAEMONS') and settings.SLAVE_DAEMONS:
            for name, endpoint in settings.SLAVE_DAEMONS.iteritems():
                print 'connecting to slave daemon %s at %s' % (name, endpoint)
                slave = Slave(name, endpoint, self._dispatcher,
                              statusHandler=self.handleSlaveStatus)
                self._slaves[name] = slave
                slave.connect()

        # start listening
        if self._opts.notificationService:
            print 'connecting to notification service %s' % self._opts.notificationService
            self._dispatcher.connectToNotificationService(self._opts.notificationService)
        for endpoint in self._opts.listenEndpoints:
            self._dispatcher.listen(endpoint,
                                    connectHandler=self.comConnectHandler,
                                    lineHandler=self.commandHandler)
        if self._opts.notificationService:
            self._dispatcher.findServices(self._opts.notificationService,
                                          announceServices = [moduleName])

        scheduler.enterPeriodic(period = CLEANUP_PERIOD,
                                action = self.cleanupChildren)
        scheduler.enterPeriodic(period = WRITE_STATUS_PERIOD,
                                action = self.writeStatus)
        scheduler.runForever()

    def stop(self, pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError, (code, msg):
            if code == errno.ESRCH:
                print 'pyraptord does not appear to be running (removing stale pid file)'
                os.unlink(self._opts.pidFile)
                return 0
            else:
                raise OSError(code, 'failed to stop pyraptord: %s' % msg)
        else:
            print 'stopping pyraptord -- sent SIGTERM to pid %d' % pid
            os.unlink(self._opts.pidFile)
            return 1

    def userStart(self):
        pid, status = self.getStatus()
        if pid == 0 or self._opts.force:
            self.start()
        else:
            print status

    def userStop(self):
        pid, status = self.getStatus()
        if pid > 0:
            self.stop(pid)
        else:
            print status

    def userRestart(self):
        pid, status = self.getStatus()
        if pid > 0:
            stopped = self.stop(pid)
            if stopped:
                print 'waiting 5 seconds for pyraptord to shut down'
                time.sleep(5)
        self.start()

    def userStatus(self):
        pid, status = self.getStatus()
        print status

    def runx(self, cmd):
        cmdFuncName = 'user' + cmd.capitalize()
        try:
            cmdFunc = getattr(self, cmdFuncName)
        except AttributeError:
            print >>sys.stderr, 'ERROR: unknown command %s' % cmd
        cmdFunc()

    @staticmethod
    def run(argv):
        opts, args = commandLineOptions.getDaemonOptsArgs(argv)
        Daemon(opts).runx(args[0])
