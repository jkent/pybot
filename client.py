# -*- coding: utf-8 -*-
# vim: set ts=4 et

import errno
import socket
import ssl

import config
from interface import SelectableInterface

debug = 'client' in config.debug


class Client(SelectableInterface):
    def __init__(self, remote, use_ssl=False):
        self.use_ssl = use_ssl
        self.remote = remote
        self.connected = False
        self.sendbuf = ''
        self.recvbuf = ''

    def fileno(self):
        return self.sock.fileno()

    def can_read(self):
        return self.connected

    def can_write(self):
        return self.connected and bool(self.sendbuf)

    def do_write(self):
        if not self.connected:
            return

        n = self._write(self.sendbuf)
        self.sendbuf = self.sendbuf[n:]

    def do_read(self):
        if not self.connected:
            return

        data = self._read()

        if not data:
            self.disconnect()
            return

        self.recvbuf += data

        if self.use_ssl:
            data_left = self.sock.pending()
            while data_left:
                self.recvbuf += self._read(data_left)
                data_left = self.sock.pending()

        parts = self.recvbuf.split('\r\n')
        lines, self.recvbuf = parts[:-1], parts[-1]

        for line in lines:
            if debug:
                print ">> %s" % line
            self.call_event('line', line)

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.use_ssl:
            self.sock = ssl.wrap_socket(self.sock)
        self.sock.setblocking(0)
        self.sock.settimeout(15)
        self.sock.connect(self.remote)
        self.connected = True
        self.call_event('connect')

    def disconnect(self):
        self.sock.close()
        self.connected = False
        self.call_event('disconnect')

    def _write(self, data):
        try:
            n = self.sock.send(data)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                self.disconnect()
                return
            elif e.errno == errno.EWOULDBLOCK:
                return
            raise
        except ssl.SSLError as e:
            if e.errno == ssl.SSL_ERROR_WANT_READ:
                return
            if e.errno == ssl.SSL_ERROR_WANT_WRITE:
                return
            raise
        return n        

    def _read(self, bufsize=1024):
        try:
            data = self.sock.recv(bufsize)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                self.disconnect()
                return
            elif e.errno == errno.EWOULDBLOCK:
                return
            raise
        except ssl.SSLError as e:
            if e.errno == ssl.SSL_ERROR_WANT_READ:
                return
            if e.errno == ssl.SSL_ERROR_WANT_WRITE:
                return
            raise

        return data

    def send(self, line):
        if debug:
            print "<< %s" % line
        line_format = "%s\r\n".encode("utf-8")
        self.sendbuf += line_format % line

