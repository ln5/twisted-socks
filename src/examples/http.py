#! /usr/bin/python

import sys
from twisted.internet import reactor, endpoints
from twsocks import SOCKSv4ClientProtocol, SOCKSWrapper
from twisted.web import client

def wrappercb(proxy):
    #print "connected to proxy ", proxy
    pass

def clientcb(content):
    print content
    reactor.stop()

def main():
    url = sys.argv[1]
    dest = client._parse(url) # scheme, host, port, path
    proxy = (None, 'localhost', 1080, True, None, None)
    endpoint = endpoints.TCP4ClientEndpoint(reactor, dest[1], dest[2])
    wrapper = SOCKSWrapper(reactor, proxy[1], proxy[2], endpoint)
    f = client.HTTPClientFactory(url)
    f.deferred.addCallback(clientcb)
    d = wrapper.connect(f)
    d.addCallback(wrappercb)
    reactor.run()

if '__main__' == __name__:
    main()
