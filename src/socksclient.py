# Copyright (c) 2011-2013, The Tor Project
# See LICENSE for the license.

import inspect
import socket
import struct
from zope.interface import implements
from twisted.internet import defer
from twisted.internet.interfaces import IStreamClientEndpoint, IReactorTime
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet.endpoints import _WrappingFactory

class SOCKSError(Exception):
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return repr(self.val)

class SOCKSv4ClientProtocol(Protocol):
    buf = ''

    def noteTime(self, event):
        if self._timer:
            self._timestamps[event] = self._timer.seconds()

    def SOCKSConnect(self, host, port):
        # only socksv4a for now
        ver = 4
        cmd = 1                 # stream connection
        user = '\x00'
        dnsname = ''
        try:
            addr = socket.inet_aton(host)
        except socket.error:
            addr = '\x00\x00\x00\x01'
            dnsname = '%s\x00' % host
        msg = struct.pack('!BBH', ver, cmd, port) + addr + user + dnsname
        self.transport.write(msg)
        self.noteTime('REQUEST')

    def verifySocksReply(self, data):
        """
        Return True on success and False on need-more-data or error.
        In the case of an error, the connection is closed and the
        handshakeDone errback is invoked with a SOCKSError exception
        before False is returned.
        """
        if len(data) < 8:
            return False
        if ord(data[0]) != 0:
            self.transport.loseConnection()
            self.handshakeDone.errback(SOCKSError((1, "bad data")))
            return False
        status = ord(data[1])
        if status != 0x5a:
            self.transport.loseConnection()
            self.handshakeDone.errback(SOCKSError(
                    (status, "request not granted: %d" % status)))
            return False
        return True

    def isSuccess(self, data):
        self.buf += data
        return self.verifySocksReply(self.buf)

    def connectionMade(self):
        self.noteTime('CONNECT')
        self.noteTime('NEGOTIATE')
        self.SOCKSConnect(self.postHandshakeEndpoint._host,
                          self.postHandshakeEndpoint._port)

    def dataReceived(self, data):
        if self.isSuccess(data):
            self.noteTime('RESPONSE')
            # Build protocol from provided factory and transfer control to it.
            self.transport.protocol = self.postHandshakeFactory.buildProtocol(
                self.transport.getHost())
            self.transport.protocol.transport = self.transport
            self.transport.protocol.connectionMade()
            self.handshakeDone.callback(self.transport.getPeer())


class SOCKSv4ClientFactory(ClientFactory):
    protocol = SOCKSv4ClientProtocol

    def buildProtocol(self, addr):
        r=ClientFactory.buildProtocol(self, addr)
        r.postHandshakeEndpoint = self.postHandshakeEndpoint
        r.postHandshakeFactory = self.postHandshakeFactory
        r.handshakeDone = self.handshakeDone
        r._timestamps = self._timestamps
        r._timer = self._timer
        return r


class SOCKSWrapper(object):
    implements(IStreamClientEndpoint)
    factory = SOCKSv4ClientFactory

    def __init__(self, reactor, host, port, endpoint, timestamps=None):
        self._host = host
        self._port = port
        self._reactor = reactor
        self._endpoint = endpoint
        self._timestamps = None
        self._timer = None
        if timestamps is not None:
            self._timestamps = timestamps
            self._timer = IReactorTime(reactor)

    def noteTime(self, event):
        if self._timer:
            self._timestamps[event] = self._timer.seconds()

    def connect(self, protocolFactory):
        """
        Return a deferred firing when the SOCKS connection is established.
        """

        def createWrappingFactory(f):
            """
            Wrap creation of _WrappingFactory since __init__() doesn't
            take a canceller as of Twisted 12.1 or something.
            """
            if len(inspect.getargspec(_WrappingFactory.__init__)[0]) == 3:
                def _canceller(deferred):
                    connector.stopConnecting()
                    deferred.errback(
                        error.ConnectingCancelledError(
                            connector.getDestination()))
                return _WrappingFactory(f, _canceller)
            else:                           # Twisted >= 12.1.
                return _WrappingFactory(f)

        self.noteTime('START')
        try:
            # Connect with an intermediate SOCKS factory/protocol,
            # which then hands control to the provided protocolFactory
            # once a SOCKS connection has been established.
            f = self.factory()
            f.postHandshakeEndpoint = self._endpoint
            f.postHandshakeFactory = protocolFactory
            f.handshakeDone = defer.Deferred()
            f._timestamps = self._timestamps
            f._timer = self._timer
            wf = createWrappingFactory(f)
            self._reactor.connectTCP(self._host, self._port, wf)
            self.noteTime('SOCKET')
            return f.handshakeDone
        except:
            return defer.fail()
