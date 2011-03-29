
import re, time
from string import Template
from geocamPycroraptor.ShadowDict import ShadowDict
import geocamPycroraptor.exceptions

def camelCase(s):
    # FOO_BAR -> fooBar
    return re.sub('_(\w)', lambda m: m.group(1).upper(), s.lower())

def splitSettings(settings):
    varsList = [(k, v) for k, v in vars(settings).iteritems()
                if k == k.upper()]
    localSettings = ShadowDict(dict(((camelCase(k[6:]), v) for k, v in varsList
                                     if k.startswith('LOCAL_'))))
    sharedSettings = ShadowDict(dict(((camelCase(k), v) for k, v in varsList
                                if not k.startswith('LOCAL_'))))
    return localSettings, sharedSettings

def _expandVal0(val, env):
    if '$' in val:
        escaped = re.sub('\$\$', '00DOLLAR00', val)
        try:
            expanded = Template(escaped).substitute(env)
        except Exception, err:
            print 'val:', val
            print 'env:', env
            raise err
        return _expandVal0(expanded, env)
    else:
        return val

def expandVal(val, env):
    if isinstance(val, str):
        expanded = _expandVal0(val, env)
        unescaped = re.sub('00DOLLAR00', '$', expanded)
        return unescaped
    else:
        return val

def _dotLookup(key, env, write):
    env['datetime'] = time.strftime('%Y-%m-%d-%H%M%S')
    allElts = key.split('.')
    elts = allElts[:-1]
    namespace = env
    writable = False
    for elt in elts:
        if callable(namespace):
            namespace = namespace()
        if hasattr(namespace, '_writable'):
            writable = True
        try:
            namespace = namespace[elt]
        except KeyError:
            raise KeyError(key)
    if write and not writable:
        raise geocamPycroraptor.exceptions.ImmutableObject(key)
    return namespace, allElts[-1]

def getVariable(key, env):
    namespace, varName = _dotLookup(key, env, write=False)
    try:
        val = namespace[varName]
    except KeyError:
        raise KeyError(key)
    return expandVal(val, env)

def setVariable(key, val, env):
    namespace, varName = _dotLookup(key, env, write=True)
    namespace[varName] = val

def updateVariable(key, updateDict, env):
    namespace, _ = _dotLookup('%s.dummy' % key, env, write=True)
    for k, v in updateDict.iteritems():
        namespace[k] = v

def delVariable(key, env):
    namespace, varName = _dotLookup(key, env)
    try:
        del namespace[varName]
    except KeyError:
        raise KeyError(key)
