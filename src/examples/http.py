#! /usr/bin/env python

# Copyright (c) 2011-2012, Linus Nordberg
# See LICENSE for details.

import sys
from twisted.internet import reactor, endpoints
from socksclient import SOCKSv4ClientProtocol, SOCKSWrapper
from twisted.web import client

def wrappercb(proxy):
    print "connected to proxy", proxy
    pass

def clientcb(content):
    print "ok, got: %s" % content[:120]
    reactor.stop()

def main():
    def sockswrapper(proxy, url):
        dest = client._parse(url) # scheme, host, port, path
        endpoint = endpoints.TCP4ClientEndpoint(reactor, dest[1], dest[2])
        return SOCKSWrapper(reactor, proxy[1], proxy[2], endpoint)

    url = sys.argv[1]
    proxy = (None, 'localhost', 9050, True, None, None)

    f = client.HTTPClientFactory(url)
    f.deferred.addCallback(clientcb)
    sw = sockswrapper(proxy, url)
    d = sw.connect(f)
    d.addCallback(wrappercb)

    if len(sys.argv) > 2:
        url2 = sys.argv[2]
        proxy2 = (None, 'localhost', 1080, True, None, None)
        f2 = client.HTTPClientFactory(url)
        f2.deferred.addCallback(clientcb)
        sw2 = sockswrapper(proxy2, url2)
        d2 = sw2.connect(f2)
        d2.addCallback(wrappercb)

    reactor.run()

if '__main__' == __name__:
    main()
