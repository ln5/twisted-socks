#! /usr/bin/env python

# Copyright (c) 2011-2013, The Tor Project
# See LICENSE for the license.

import sys
from urlparse import urlparse
from twisted.internet import reactor, endpoints
from socksclient import SOCKSv4ClientProtocol, SOCKSWrapper
from twisted.web import client

class mything:
    def __init__(self):
        self.npages = 0
        self.timestamps = {}

    def wrappercb(self, proxy):
        print "connected to proxy", proxy

    def clientcb(self, content):
        print "ok, got: %s" % content[:120]
        print "timetamps " + repr(self.timestamps)
        self.npages -= 1
        if self.npages == 0:
            reactor.stop()

    def sockswrapper(self, proxy, url):
        dest = urlparse(url)
        assert dest.port is not None, 'Must specify port number.'
        endpoint = endpoints.TCP4ClientEndpoint(reactor, dest.hostname, dest.port)
        return SOCKSWrapper(reactor, proxy[1], proxy[2], endpoint, self.timestamps)

def main():
    thing = mything()

    # Mandatory first argument is a URL to fetch over Tor (or whatever
    # SOCKS proxy that is running on localhost:9050).
    url = sys.argv[1]
    proxy = (None, 'localhost', 9050, True, None, None)

    f = client.HTTPClientFactory(url)
    f.deferred.addCallback(thing.clientcb)
    sw = thing.sockswrapper(proxy, url)
    d = sw.connect(f)
    d.addCallback(thing.wrappercb)
    thing.npages += 1

    # Optional second argument is a URL to fetch over whatever SOCKS
    # proxy that is running on localhost:1080 (possibly `twistd -n socks').
    if len(sys.argv) > 2:
        url2 = sys.argv[2]
        proxy2 = (None, 'localhost', 1080, True, None, None)
        f2 = client.HTTPClientFactory(url)
        f2.deferred.addCallback(thing.clientcb)
        sw2 = thing.sockswrapper(proxy2, url2)
        d2 = sw2.connect(f2)
        d2.addCallback(thing.wrappercb)
        thing.npages += 1

    reactor.run()

if '__main__' == __name__:
    main()
