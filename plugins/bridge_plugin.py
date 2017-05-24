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
        port = self.plugin.bot.config.getint(self.plugin.name, 'port', fallback=65432)
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
            token = self.server.plugin.bot.config.get(self.server.plugin.name, 'token')
            if obj['token'] != token:
                self.disconnect()
                return
                
            self.realm = obj.get('realm', None)
            self.authenticated = True
            return
        
        if objtype == 'message':
            channel = obj.get('channel', None)
            username = obj.get('username', None)
            message = obj.get('message', None)

            if not channel or not username or not message:
                self.disconnect()
                return

            self.server.plugin.process_input(self.realm, channel, username, message)

    def send_obj(self, obj):
        self.sendbuf += json.dumps(obj) + '\r\n'

    def disconnect(self):
        self.connected = False
        self.sock.close()
        self.server.plugin.bot.core.selectable.remove(self)
        self.server.clients.remove(self)

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
        self.load_streams()
        
    def on_unload(self, reloading):
        self.server.shutdown()

    def load_streams(self):
        streams = self.bot.config.get(self.name, 'input_streams')
        self.input_streams = []
        for stream_str in streams.split():
            try:
                realm, channel, stream_id = stream_str.split(':')
            except:
                continue

            stream = {'realm': realm, 'channel': channel, 'id': int(stream_id)}
            self.input_streams.append(stream)

        streams = self.bot.config.get(self.name, 'output_streams')
        self.output_streams = []
        for stream_str in streams.split():
            try:
                realm, channel, stream_id = stream_str.split(':')
            except:
                continue

            stream = {'realm': realm, 'channel': channel, 'id': int(stream_id)}
            self.output_streams.append(stream)
    
    @hook
    def bridge_reload_trigger(self, msg, args, argstr):
        self.load_streams()
        msg.reply("reloaded input/output streams")

    @hook
    def privmsg_command(self, msg):
        if not msg.channel:
            return
        
        if msg.trigger:
            return

        self.process_input('master', msg.channel, msg.source, msg.param[-1])

    def process_input(self, realm, channel, username, message):
        input_ids = [stream['id'] for stream in self.input_streams if stream['realm'] == realm and stream['channel'] == channel]
        output_streams = [stream for stream in self.output_streams if stream['id'] in input_ids]
        for output_stream in output_streams:
            if output_stream['realm'] == 'master':
                self.bot.privmsg(channel, '<%s> %s' % (username, message))
            else:
                for client in self.server.clients:
                    if getattr(client, 'realm', None) == output_stream['realm']:
                        obj = {'type': 'message', 'channel': channel, 'username': username, 'message': message}
                        client.send_obj(obj)
