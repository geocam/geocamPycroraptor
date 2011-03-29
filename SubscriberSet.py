
import simplejson

from irgCom.WeakSet import WeakSet

from geocamPycroraptor.PycroEncoder import PycroEncoder
from geocamPycroraptor.printTraceback import printTraceback

class SubscriberSet(WeakSet):
    def write(self, obj):
        text = simplejson.dumps(obj, cls=PycroEncoder)
        x = list(self)
        for subscriber in self:
            if not subscriber.connected:
                continue
            try:
                subscriber.write(text + '\n')
            except:
                printTraceback()
