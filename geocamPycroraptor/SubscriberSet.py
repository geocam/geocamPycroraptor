# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from geocamPycroCom.WeakSet import WeakSet

from geocamPycroraptor.PycroEncoder import PycroEncoder
from geocamPycroraptor.printTraceback import printTraceback
from geocamPycroraptor import anyjson as json


class SubscriberSet(WeakSet):
    def write(self, obj):
        text = json.dumps(obj, cls=PycroEncoder)
        for subscriber in self:
            if not subscriber.connected:
                continue
            try:
                subscriber.write(text + '\n')
            except:  # pylint: disable=W0702
                printTraceback()
