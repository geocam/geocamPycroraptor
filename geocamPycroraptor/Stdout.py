# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import sys
import os
import errno
import traceback

from geocamPycroCom import asyncore # patched version

class Stdout(asyncore.file_dispatcher):
    def __init__(self, childStdoutReadFd, logger, parentTask, streamName):
        asyncore.file_dispatcher.__init__(self, childStdoutReadFd)
        self._logger = logger
        self._alreadyClosed = False
        self._parentTask = parentTask
        self._streamName = streamName

    def close(self):
        if not self._alreadyClosed:
            self._alreadyClosed = True
            try:
                asyncore.file_dispatcher.close(self)
            except OSError, oe:
                # we get these errors on broken pipe or file already closed, no problem
                if oe.errno not in (errno.PIPE, errno.EBADF):
                    raise oe

    def writable(self):
        return False

    def readable(self):
        return not self._alreadyClosed

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_error(self):
        errClass, errObject, errTB = sys.exc_info()[:3]
        traceback.print_tb(errTB)
        print >>sys.stderr, '%s.%s: %s' % (errClass.__module__,
                                           errClass.__name__,
                                           errObject)
        self.close()
        if errClass is KeyboardInterrupt:
            sys.exit(0)

    def handle_read(self):
        if self.readable():
            try:
                newText = self.recv(8192)
            except OSError, oe:
                # EIO on ptty read indicates EOF under Linux
                # see http://bugs.python.org/issue5380
                if oe.errno != errno.EIO:
                    raise
                #self._parentTask._logText('child closed %s stream, but it may still be running' % self._streamName)
                self.close()
            else:
                if newText:
                    self._logger.write(newText)

    def handle_expt(self):
        self.close()
