
import os, optparse, imp
import re
import platform
from pycroraptor import settings

DEFAULT_SETTINGS_FILE = os.environ.get('PYCRORAPTOR_SETTINGS_FILE', None)
DEFAULT_ENDPOINT = os.environ.get('PYCRORAPTOR_ENDPOINT', 'tcp:localhost:8085')

def commaSplit(option, opt, value, parser):
    if value:
        elts = value.split(',')
    else:
        elts = []
    setattr(parser.values, option.dest, elts)

def getOptParser():
    parser = optparse.OptionParser()
    parser.add_option('-s', '--settings',
                      default=DEFAULT_SETTINGS_FILE,
                      help='Settings file to load [%default]')
    parser.add_option('-n', '--notificationService',
                      default=None,
                      help='Endpoint or CORBA name for notification service [%default]')
    parser.add_option('--nameService',
                      default=None,
                      help='Endpoint for CORBA naming service [%default]')
    return parser

def readSettings(settingsFileName):
    if not os.path.lexists(settingsFileName):
        raise IOError('settings file "%s" does not exist' % settingsFileName)
    userSettings = imp.load_source('pycroraptor.userSettings', settingsFileName)
    for k, v in vars(userSettings).iteritems():
        setattr(settings, k, v)

def getClientOptsArgs(argv):
    parser = getOptParser()
    parser.set_usage('usage: %prog [OPTIONS]')
    parser.add_option('-e', '--exec',
                      default=None, dest='startupCommand',
                      help='Execute specified command and quit')
    parser.add_option('-d', '--daemons',
                      default=[DEFAULT_ENDPOINT],
                      type='string', action='callback',
                      callback=commaSplit, dest='daemons',
                      help=('Comma-separated list of pyraptord endpoints to connect to [%s]'
                            % DEFAULT_ENDPOINT))
    opts, args = parser.parse_args(args = argv[1:])
    if opts.settings:
        readSettings(opts.settings)
    return opts, args

def getDaemonOptsArgs(argv):
    parser = getOptParser()
    parser.set_usage('usage: %prog [OPTIONS] <start|stop|restart|status>')
    parser.add_option('-f', '--force',
                      action='store_true', default=False,
                      help='Force start action even if pyraptord appears to be running')
    parser.add_option('--pidFile',
                      default='from settings',
                      help='Pid file to track pyraptord status [%default]')
    parser.add_option('--logFile',
                      default='from settings',
                      help='Log file to write [%default]')
    parser.add_option('--statusFile',
                      default='from settings',
                      help='Status file to write [%default]')
    parser.add_option('--startupGroup',
                      default='startup',
                      help='Group of tasks to run at startup [%default]')
    parser.add_option('-l', '--listenEndpoints',
                      default=[DEFAULT_ENDPOINT],
                      type='string', action='callback',
                      callback=commaSplit, dest='listenEndpoints',
                      help=('Comma-separated list of endpoints to listen on [%s]'
                            % DEFAULT_ENDPOINT))
    parser.add_option('--logComm',
                      action='store_true', default=False,
                      help='Enables logging of all comm traffic with clients')
    parser.add_option('--name',
                      default=re.sub('\..*$', '', platform.node()),
                      help='Name of this daemon [%default]')
    parser.add_option('--foreground',
                      default=False, action='store_true',
                      help='If set, do not daemonize')
    opts, args = parser.parse_args(args = argv[1:])
    if opts.settings:
        readSettings(opts.settings)
    if opts.pidFile == 'from settings':
        opts.pidFile = settings.LOCAL_DAEMON_PID_FILE
    if opts.logFile == 'from settings':
        opts.logFile = settings.LOCAL_DAEMON_LOG_FILE
    if opts.statusFile == 'from settings':
        opts.statusFile = settings.LOCAL_DAEMON_STATUS_FILE
    if len(args) != 1:
        parser.error('expected exactly one command')
    return opts, args
