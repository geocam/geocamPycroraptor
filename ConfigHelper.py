
from geocamPycroraptor.Printable import Printable
from geocamPycroraptor.ConfigDict import ConfigDict

defaultProcessConfig = ConfigDict(cmd = '$name',
                                  workingDir = '/tmp',
                                  env = {},
                                  log = None,
                                  stopCmd = 'kill -TERM $pid',
                                  stopBackupCmd = 'kill -KILL $pid',
                                  stopBackupDelay = 5)

