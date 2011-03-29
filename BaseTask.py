
from geocamPycroraptor.Printable import Printable
from geocamPycroraptor.SubscriberSet import SubscriberSet

class BaseTask(Printable):
    def __init__(self, name, parent):
        self.name = name
        self._parent = parent
        self._env = parent._env['settings']['tasks'][name]
        self._statusSubscribers = SubscriberSet()

    def setStatus(self, status):
        self.status = status
        self._statusSubscribers.write(['status', self.name, status])

    def isRunning(self):
        return self.status != None and self.status['status'] == 'running'

    def isLocal(self):
        pass # implement in derived class

    def _getConfig(self, field):
        return self._expandWithPid(self._env[field])

    ######################################################################
    # functions to be called from client
    ######################################################################

    def start(self, params={}):
        '''return 1 if a task was started'''
        if self.isRunning():
            return 0
        else:
            self.start0(params)
            return 1

    def stop(self):
        '''return 1 if a task was stopped'''
        if self.isRunning():
            self.stop0()
            return 1
        else:
            return 0
    
    def restart(self, params={}):
        '''return status before restart'''
        pass

    def getStatus(self):
        pass

    def writeStdin(self, text):
        pass

    ######################################################################
    # functions to be called from parent daemon level
    ######################################################################

    def cleanup(self):
        pass
        
        
