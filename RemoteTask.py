
import os
import sys

from geocamPycroraptor.Printable import Printable
from geocamPycroraptor.SubscriberSet import SubscriberSet
from geocamPycroraptor.BaseTask import BaseTask

class RemoteTask(BaseTask):
    def __init__(self, name, parent, slave):
        super(RemoteTask, self).__init__(name, parent)
        self._slave = slave
        self.status = None

    def isLocal(self):
        return False

    ######################################################################
    # functions to be called from client
    ######################################################################

    def start0(self, params={}):
        self._slave.writeObject(['start', self.name, params])

    def stop0(self):
        self._slave.writeObject(['stop', self.name])
    
    def restart(self, params={}):
        statusWas = 'was' + self.status['status'].capitalize()
        self._slave.writeObject(['restart', self.name])
        return statusWas

    def getStatus(self):
        return self.status

    def writeStdin(self, text):
        self._slave.writeObject(['stdin', self.name, repr(text)])

    ######################################################################
    # functions to be called from parent daemon level
    ######################################################################

    def cleanup(self):
        pass
