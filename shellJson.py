
import re, json
import geocamPycroraptor.exceptions
from geocamPycroraptor import anyjson as json

JSON_RESERVED_WORDS = dict.fromkeys(['null'])

def trisplit(s):
    match = re.search('^([^\s]+)(\s+)([^\s].*)$', s)
    if match:
        return match.group(1), match.group(2), match.group(3)
    else:
        return s, '', ''

def isIdentifier(s):
    return (re.search('^-?[a-zA-Z][a-zA-Z_0-9\.]*$', s)
            and s not in JSON_RESERVED_WORDS)

def parseTerm(s):
    if isIdentifier(s):
        return s
    else:
        try:
            obj = json.loads(s)
        except ValueError, err:
            raise geocamPycroraptor.exceptions.SyntaxError(*err.args)
        else:
            if isinstance(obj, (str, unicode)):
                # quote the string to retain distinction with bareword
                obj = '"%s"' % obj
            return obj

def parseShellJsonShell(cmd):
    parsedCmd = []
    while cmd:
        head, wspace, cmd = trisplit(cmd)
        while True:
            try:
                parsedHead = parseTerm(head)
            except geocamPycroraptor.exceptions.SyntaxError:
                if cmd:
                    head2, wspace2, cmd = trisplit(cmd)
                    head = head + wspace + head2
                    wspace = wspace2
                else:
                    raise
            else:
                parsedCmd.append(parsedHead)
                break
    return parsedCmd

def parseShellJsonStrict(cmd):
    try:
        return json.loads(cmd)
    except ValueError, err:
        raise geocamPycroraptor.exceptions.SyntaxError(*err.args)

def parseShellJson(cmd):
    cmd = cmd.strip()
    if cmd.startswith('['):
        return parseShellJsonStrict(cmd)
    else:
        return parseShellJsonShell(cmd)

if __name__ == "__main__":
    # test
    print parseShellJson('foo bar zoo')
    print parseShellJson('foo "bar zoo"')
    print parseShellJson('foo {"zoo": 3}')
    print parseShellJson('foo {"zoo": [3, 4, 5]}')
    print parseShellJson('[3, 4, 5]')
    print parseShellJson('["foo", "goo", {"x": 2}]')
    print parseShellJson('kill -a')
    try:
        print parseShellJson('foo {"zoo":')
    except geocamPycroraptor.exceptions.SyntaxError:
        print 'last call raised error as expected'
    else:
        print 'oops, how did that parse?'
