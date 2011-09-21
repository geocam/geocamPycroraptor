# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from geocamPycroraptor.ConfigDict import ConfigDict
import geocamPycroraptor.errors
from geocamPycroraptor import anyjson as json


class StatusGetter:
    def __init__(self, daemon):
        self._daemon = daemon

    def __getitem__(self, taskName):
        return self._daemon.getTask(taskName).status

    def __setitem__(self, taskName, val):
        raise geocamPycroraptor.errors.ImmutableObject('task status is immutable')

    def asDict(self):
        allSettings = self._daemon._env['settings']
        allTaskSettings = allSettings['tasks']
        allTaskNames = allTaskSettings.keys()
        return dict(((k, self[k]) for k in allTaskNames
                     if self._daemon.isTask(k) and self[k] is not None))


class PycroEncoder(json.JSONEncoder):
    def default(self, obj):  # pylint: disable=E0202
        if isinstance(obj, (ConfigDict, StatusGetter)):
            return obj.asDict()
        else:
            return json.JSONEncoder.default(self, obj)
