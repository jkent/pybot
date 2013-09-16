# -*- coding: utf-8 -*-
# vim: set ts=4 et

import errno
import socket
import ssl
import time
import traceback
from interfaces import SelectableInterface


class RemoteServer(SelectableInterface):
    def __init__(self, remote, use_ssl=False):
        self.use_ssl = use_ssl
        self.remote = remote
        self.connected = False
        self.writebuf = ''
        self.readbuf = ''

    def fileno(self):
        return self.sock.fileno()

    def can_read(self):
        return True

    def can_write(self):
        return bool(self.writebuf)

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.use_ssl:
            self.sock = ssl.wrap_socket(self.sock)
        self.sock.setblocking(0)
        self.sock.settimeout(15)
        self.sock.connect(self.remote)
        self.connected = True

    def do_write(self):
        try:
            n = self.sock.send(self.writebuf)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                self.connected = False
                return
            if e.errno == errno.EWOULDBLOCK:
                return
            raise
        except ssl.SSLError as e:
            if e.errno == ssl.SSL_ERROR_WANT_READ:
                return
            raise

        self.writebuf = self.writebuf[n:]

    def do_read(self):
        try:
            data = self.sock.recv(1024)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                self.connected = False
                return
            if e.errno == errno.EWOULDBLOCK:
                return
            raise
        except ssl.SSLError as e:
            if e.errno == ssl.SSL_ERROR_WANT_READ:
                return
            raise

        if not data: # eof/closed
            self.connected = False
            return

        if self.use_ssl:
            data_left = self.sock.pending()
            while data_left:
                data += self.sock.recv(data_left)
                data_left = self.sock.pending()

        self.readbuf += data
        parts = self.readbuf.split('\r\n')
        lines, self.readbuf = parts[:-1], parts[-1]
        for line in lines:
            print ">> %s" % line
            try:
                self.process_line(line)
            except:
                traceback.print_exc()


    def write(self, line):
        print "<< %s" % line
        self.writebuf += '%s\r\n' % line

