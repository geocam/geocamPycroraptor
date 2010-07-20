
from pycroraptor.Printable import Printable
from pycroraptor.ConfigDict import ConfigDict

defaultProcessConfig = ConfigDict(cmd = '$name',
                                  workingDir = '/tmp',
                                  env = {},
                                  log = None,
                                  host = None,
                                  stopCmd = 'kill -TERM $pid',
                                  stopBackupCmd = 'kill -KILL $pid',
                                  stopBackupDelay = 5)

