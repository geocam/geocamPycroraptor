
from geocamPycroCom.WeakSet import WeakSet

from geocamPycroraptor.PycroEncoder import PycroEncoder
from geocamPycroraptor.printTraceback import printTraceback
from geocamPycroraptor import anyjson as json

class SubscriberSet(WeakSet):
    def write(self, obj):
        text = json.dumps(obj, cls=PycroEncoder)
        x = list(self)
        for subscriber in self:
            if not subscriber.connected:
                continue
            try:
                subscriber.write(text + '\n')
            except:
                printTraceback()
