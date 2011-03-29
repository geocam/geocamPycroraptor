
import os
import datetime
import re
from geocamPycroraptor.ExpandVariables import expandVal

UNIQUE_REGEX = r'\$\{unique\}|\$unique\b'

def getFileNameTimeString(timestamp=None):
    if timestamp == None:
        timestamp = datetime.datetime.now()
    return timestamp.strftime('%Y-%m-%d-%H%M%S')

def getTimeString(timestamp=None):
    if timestamp == None:
        timestamp = datetime.datetime.now()
    return timestamp.isoformat()

def openLogFromFileName(fname, mode='a+'):
    logDir = os.path.dirname(fname)
    if not os.path.exists(logDir):
        os.makedirs(logDir)
    logFile = file(fname, mode, 0)
    return logFile

def _expandUniq(fname, counterStr, env):
    fnameWithUniq = re.sub(UNIQUE_REGEX, counterStr, fname)
    return expandVal(fnameWithUniq, env)

def _forceSymLink(src, target):
    if os.path.lexists(target):
        if os.path.islink(target):
            os.unlink(target)
        else:
            raise Exception('_forceSymLink: %s exists and is not a symlink, not overwriting'
                            % target)
    else:
        if not os.path.isdir(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target))
    try:
        os.symlink(src, target)
    except OSError, err:
        raise OSError('%s [in symlink "%s" "%s"]'
                      % (str(err), src, target))

def _findUniqueFileAndSetSymLink(fnameTemplate, env):
    if re.search(UNIQUE_REGEX, fnameTemplate):
        for i in xrange(0, 10000):
            uniqStr = '%s-%d' % (getFileNameTimeString(), i)
            fname = _expandUniq(fnameTemplate, uniqStr, env)
            if not os.path.exists(fname):
                symSrc = os.path.basename(fname)
                symTarget = _expandUniq(fnameTemplate, 'latest', env)
                _forceSymLink(symSrc, symTarget)
                return fname
        raise Exception('could not find unique log file name; exhausted counter at 9999')
    else:
        return expandVal(fnameTemplate)

def openLogFromTemplate(fnameTemplate, env):
    fname = _findUniqueFileAndSetSymLink(fnameTemplate, env)
    return (fname, openLogFromFileName(fname))

class TimestampLine:
    def __init__(self, streamName, lineType, text, timestamp=None):
        if timestamp == None:
            timestamp = datetime.datetime.now()
        self.streamName = streamName
        self.lineType = lineType
        self.text = text
        self.timestamp = timestamp

class LineSource(object):
    def __init__(self, lineHandler=None):
        self._lineHandlers = {}
        self._lineHandlerCount = 0
        if lineHandler:
            self.addLineHandler(lineHandler)
    def addLineHandler(self, handler):
        handlerRef = self._lineHandlerCount
        self._lineHandlerCount += 1
        self._lineHandlers[handlerRef] = handler
        return handlerRef
    def delLineHandler(self, handlerRef):
        del self._lineHandlers[handlerRef]
    def handleLine(self, tsline):
        for hnd in self._lineHandlers.itervalues():
            hnd(tsline)

class TimestampLineParser(LineSource):
    def __init__(self, streamName, lineHandler = None, maxLength=None):
        if maxLength == None:
            maxLength = 160
        LineSource.__init__(self, lineHandler)
        self._streamName = streamName
        self._maxLength = maxLength
        self._ibuffer = []
        self._buflen = 0
        self._lastLineType = None
    def collect_incoming_data(self, text):
        self._ibuffer += text
        self._buflen += len(text)
    def found_terminator(self, terminator):
        if terminator == '\r\n' or terminator == '\n':
            lineType = 'n'
        elif terminator == '\r':
            lineType = 'r'
        else:
            lineType = 'c'
        text = ''.join(self._ibuffer)
        if not (lineType == 'r' and text == '' and self._lastLineType != 'c'):
            self._lastLineType = lineType
            self.handleLine(TimestampLine(self._streamName, lineType, text))
        self._ibuffer = ''
        self._buflen = 0
    def write(self, text):
        while len(text) > 0:
            spaceRemaining = self._maxLength - self._buflen
            if len(text) >= spaceRemaining:
                startOfNextSegmentIndex = self._write0(text[:spaceRemaining])
                self.flush()
            else:
                startOfNextSegmentIndex = self._write0(text)
            text = text[startOfNextSegmentIndex:]
    def flush(self):
        if self._buflen > 0:
            self.found_terminator(None)
    def _write0(self, text):
        m = re.search('(\r\n)|\r|\n', text)
        if m:
            endOfSegmentIndex = m.start(0)
            self.collect_incoming_data(text[:endOfSegmentIndex])
            terminator = m.group(0)
            self.found_terminator(terminator)
            startOfNextSegmentIndex = m.end(0)
        else:
            self.collect_incoming_data(text)
            startOfNextSegmentIndex = len(text)
        return startOfNextSegmentIndex

class LineBuffer(LineSource):
    def __init__(self, lineHandler=None, maxSize=2048):
        LineSource.__init__(self, lineHandler)
        self._maxSize = maxSize
        self._lines = []
        self._lineCount = 0
    def addLine(self, tsline):
        DELETE_SIZE = self._maxSize // 2
        if len(self._lines) == self._maxSize - DELETE_SIZE:
            del self._lines[0:DELETE_SIZE]
        tsline.lineCount = self._lineCount
        self._lines.append(tsline)
        self._lineCount += 1
        self.handleLine(tsline)
    def getLines(self, minTime=None, maxLines=None):
        n = len(self._lines)
        if minTime:
            minIndex = n
            for i in reversed(xrange(0, n)):
                if line.timestamp < minTime:
                    minIndex = i+1
                    break
        else:
            minIndex = 0
        if maxLines:
            minIndex = max(minIndex, n-maxLines)
        return self._lines[minIndex:]

class TimestampLineLogger:
    def __init__(self, stream):
        self._stream = stream
    def handleLine(self, tsline):
        self._stream.write('%s %s %s %s\n' % (tsline.streamName, tsline.lineType,
                                              getTimeString(tsline.timestamp), tsline.text))

class StreamLogger(TimestampLineParser):
    def __init__(self, streamName, stream, maxLength=None):
        self._logger = TimestampLineLogger(stream)
        TimestampLineParser.__init__(self, streamName, self._logger.handleLine, maxLength)
