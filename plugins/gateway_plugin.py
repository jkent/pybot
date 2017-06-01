# -*- coding: utf-8 -*-
# vim: set ts=4 et

import errno
import json
import socket
from interface import SelectableInterface

from plugin import *


class BridgeServer(SelectableInterface):
    def __init__(self, plugin):
        self.plugin = plugin
        self.clients = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = self.plugin.config_getint('port', 65432)
        listen = ('127.0.0.1', port)
        self.sock.bind(listen)
        self.sock.listen(5)
        self.connected = True
        self.plugin.bot.core.selectable.append(self)

    def fileno(self):
        return self.sock.fileno()

    def can_read(self):
        return self.connected

    def do_read(self):
        sock, _ = self.sock.accept()
        BridgeClient(self, sock)

    def shutdown(self):
        self.connected = False
        for obj in self.plugin.bot.core.selectable[:]:
            if getattr(obj, 'server', None) == self:
                obj.disconnect()
        self.plugin.bot.core.selectable.remove(self)
        self.sock.close()


class BridgeClient(SelectableInterface):
    def __init__(self, server, sock):
        self.server = server
        self.sock = sock
        self.sendbuf = ''
        self.recvbuf = ''
        self.connected = True
        self.authenticated = False
        self.server.plugin.bot.core.selectable.append(self)
        self.server.clients.append(self)
        self.realm = None

    def fileno(self):
        return self.sock.fileno()

    def can_read(self):
        return self.connected

    def can_write(self):
        return self.connected and bool(self.sendbuf)

    def do_read(self):
        data = self._read()

        if not data:
            self.disconnect()
            return

        self.recvbuf += data

        parts = self.recvbuf.split('\r\n')
        lines, self.recvbuf = parts[:-1], parts[-1]

        for line in lines:
            try:
                obj = json.loads(line)
            except:
                continue
            self.recv_obj(obj)

    def do_write(self):
        n = self._write(self.sendbuf)
        self.sendbuf = self.sendbuf[n:]

    def recv_obj(self, obj):
        objtype = obj.get('type', None) 

        if not self.authenticated:
            if objtype != 'auth':
                self.disconnect()
                return
            secret = self.server.plugin.config_get('secret')
            if obj['secret'] != secret:
                self.disconnect()
                return

            self.realm = obj.get('realm', None)
            self.authenticated = True
            self.send_obj({'type': 'authok'})
            return

        if objtype in ['message', 'action']:
            channel = obj.get('channel', None)
            username = obj.get('username', None)
            message = obj.get('message', None)

            if not channel or not username or not message:
                self.disconnect()
                return
            if objtype in ['message', 'action']:
                self.server.plugin.process_message(self.realm, channel, username, message, objtype == 'action')

    def send_obj(self, obj):
        self.sendbuf += json.dumps(obj) + '\r\n'

    def disconnect(self):
        self.connected = False
        self.sock.close()
        try:
            self.server.plugin.bot.core.selectable.remove(self)
            self.server.clients.remove(self)
        except:
            pass

    def _write(self, data):
        if type(data) == str:
            data = data.encode('utf-8')
        try:
            n = self.sock.send(data)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                self.disconnect()
                return
            elif e.errno == errno.EWOULDBLOCK:
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
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError:
            data = data.decode("latin-1")
        return data


class Plugin(BasePlugin):
    def on_load(self, reloading):
        self.server = BridgeServer(self)
        self.load_routes()
        
    def on_unload(self, reloading):
        self.server.shutdown()

    def load_routes(self):
        self.routes = []
        routes = self.config_get('routes')
        for route in routes.split():
            try:
                src_realm, src_channel, dst_realm, dst_channel = route.split(':', 3)
            except:
                continue 

            self.routes.append({'src_realm': src_realm, 'src_channel': src_channel, 'dst_realm': dst_realm, 'dst_channel': dst_channel})

    @hook
    def gateway_reload_trigger(self, msg, args, argstr):
        self.load_routes()
        msg.reply("reloaded routes")

    @hook
    def privmsg_command(self, msg):
        if not msg.channel:
            return

        if msg.trigger:
            return

        message = msg.param[-1]
        if message.startswith('\x01ACTION') and message.endswith('\x01'):
            message = message[8:-1]
            self.process_message('irc', msg.channel, msg.source, message, True)
        else:
            self.process_message('irc', msg.channel, msg.source, message)

    def process_message(self, realm, channel, username, message, is_action=False):
        routes = [route for route in self.routes if route['src_realm'] == realm and route['src_channel'] == channel]
        for route in routes:
            if route['dst_realm'] == 'irc':
                if is_action:
                    self.bot.privmsg(route['dst_channel'], '* %s %s' % (username, message))
                else:
                    self.bot.privmsg(route['dst_channel'], '<%s> %s' % (username, message))
            else:
                for client in self.server.clients:
                    if route['dst_realm'] == getattr(client, 'realm', None):
                        obj = {'type': 'action' if is_action else 'message',
                               'from_realm': realm,
                               'from_channel': channel,
                               'realm': route['dst_realm'],
                               'channel': route['dst_channel'],
                               'username': username,
                               'message': message}
                        client.send_obj(obj)
