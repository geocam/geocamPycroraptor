
from pycroraptor.Printable import Printable

class ConfigDict(Printable):
    def __init__(self, updateDict=None, **kwargs):
        self.__dict__['_contents'] = {}
        self.plusEquals(updateDict, **kwargs)
    def plusEquals(self, updateDict=None, **kwargs):
        if updateDict != None:
            self._contents.update(updateDict)
        self._contents.update(**kwargs)
        return self
    def copy(self):
        return ConfigDict(self)
    def plus(self, updateDict=None, **kwargs):
        return self.copy().plusEquals(updateDict, **kwargs)

    def __getitem__(self, k):
        return self._contents.__getitem__(k)
    def __setitem__(self, k, v):
        self._contents.__setitem__(k, v)
    def __delitem__(self, k):
        self._contents.__delitem__(k)
    def __contains__(self, k):
        return self._contents.__contains__(k)
    def __iter__(self):
        return self._contents.__iter__()
    def asDict(self):
        return self._contents
    def keys(self):
        """needed for myDict.update(myConfigDict) to work right.  generally speaking,
        can access dict methods using asDict(), e.g. myConfigDict.asDict().values()"""
        return self._contents.keys()

    def __getattr__(self, k):
        return self._contents[k]
    def __setattr__(self, k, v):
        self._contents[k] = v
