# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import optparse, signal, time

def hello(signum=None, frame=None):
    print 'hello'

def runTest():
    signal.signal(signal.SIGTERM, hello)
    while 1:
        time.sleep(1)

def main():
    parser = optparse.OptionParser()
    opts, args = parser.parse_args()
    runTest()

if __name__ == "__main__":
    main()
