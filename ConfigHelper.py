# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from geocamPycroraptor.Printable import Printable
from geocamPycroraptor.ConfigDict import ConfigDict

defaultProcessConfig = ConfigDict(cmd = '$name',
                                  workingDir = '/tmp',
                                  env = {},
                                  log = None,
                                  stopCmd = 'kill -TERM $pid',
                                  stopBackupCmd = 'kill -KILL $pid',
                                  stopBackupDelay = 5)

