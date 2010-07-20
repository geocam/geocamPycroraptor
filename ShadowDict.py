
class ShadowDict:
    def __init__(self, defaultDict):
        self._dict = {}
        self._defaultDict = defaultDict
    def __getitem__(self, key):
        try:
            return self._dict[key]
        except KeyError:
            return self._defaultDict[key]
    def __setitem__(self, key, value):
        self._dict[key] = value
    def __delitem__(self, key):
        del self._dict[key]
    def __contains__(self, key):
        return key in self._dict or key in self._defaultDict
    def __repr__(self):
        return str(dict(((k, self[k]) for k in self.keys())))
    def keys(self):
        result = self._defaultDict.keys() + self._dict.keys()
        result.sort()
        return result
