# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import os
from geocamPycroraptor.ConfigHelper import ConfigDict, defaultProcessConfig

logDir = '/tmp/pyraptord/logs'

LOCAL_DAEMON_LOG_FILE = '%s/pyraptord_${unique}.txt' % logDir
LOCAL_DAEMON_PID_FILE = '%s/pyraptord_pid.txt' % logDir
LOCAL_DAEMON_STATUS_FILE = '%s/pyraptordStatus.html' % logDir

d = defaultProcessConfig.copy() # abbreviate
d.log = '%s/${name}_${unique}.txt' % logDir

TASKS = ConfigDict()
TASKS.bc = d.plus(cmd='bc')
TASKS.echo = d.plus(cmd='echo hello')

GROUPS = ConfigDict()
GROUPS.startup = ['echo']
