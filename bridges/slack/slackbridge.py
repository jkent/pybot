# -*- coding: utf-8 -*-
# vim: set ts=4 et

import errno
import json
import re
from select import select
from slackclient import SlackClient as Slack
import socket
import time

from interface import SelectableInterface
import config


slack_mention_re = re.compile('<@(\w+)>')
slack_channel_re = re.compile('<#(\w+)(?:\|([\w-]+))?>')
bridge_mention_re = re.compile('(^|\s)@(\w+)(\s|$)')


class SlackClient(SelectableInterface):
    def __init__(self, bridge):
        SelectableInterface.__init__(self)
        self.bridge = bridge 
        self.users = {}
        self.channels = {}
        self.last_message = 0
        self.connected = False
        self.backoff = 0
        self.reconnect_time = 0

        self.slack = Slack(config.bot_token)
        self.connect()

    def connect(self):
        try:
            if not self.slack.rtm_connect():
                raise Exception('Error connecting to slack')
        except:
            self.backoff = min(60, self.backoff + (self.backoff//2) + 1)
            self.reconnect_time = time.time() + self.backoff
            print('Error connecting to slack, backoff %ds' % self.backoff)
            return
        self.last_message = time.time()
        self.connected = True
        self.backoff = 0
        self.reconnect_time = 0
        
    def fileno(self):
        return self.slack.server.websocket.sock.fileno()

    def can_read(self):
        return bool(self.slack.server.websocket) and bool(self.slack.server.websocket.sock)
    
    def do_read(self):
        try:
            messages = self.slack.rtm_read()
        except:
            self.connected = False
            return
        if messages:
            self.last_message = time.time()
        for message in messages:
            _type = message.get('type', None)
            if _type == 'hello':
                self.handle_hello(message)
            elif _type == 'message':
                self.handle_message(message)
            elif _type == 'user_change':
                self.handle_user_change(message['user'])
            elif _type == 'channel_change':
                self.handle_channel_changs(message['channel'])

    def do_tick(self, now):
        if not self.connected:
            if self.reconnect_time <= now:
                self.reconnecting = True
                self.connect()

        if self.last_message + 5 < now:
            try:
                self.slack.server.ping()
            except:
                self.connected = False

    def handle_hello(self, message):
            print("Connected to Slack")
            data = self.slack.api_call(
                'users.list')
            if data['ok']:
                for user in data['members']:
                    _id = user['id']
                    self.users[_id] = user

    def handle_message(self, message):
        if 'bot_id' in message:
            return

        if message.get('hidden', None) == True:
            return

        subtype = message.get('subtype', None)
        if subtype not in [None, 'me_message']:
            return

        channel = self.lookup_channel(message['channel'])
        if not channel:
            return

        user = self.lookup_user(message['user'])

        def mention_replace(var):
            _id = var.group(1)
            user = self.lookup_user(_id)
            return '@' + user['name']
        text = slack_mention_re.sub(mention_replace, message['text'])

        def channel_replace(var):
            _id = var.group(1)
            channel = self.lookup_channel(_id)
            return '#' + channel['name']
        text = slack_channel_re.sub(channel_replace, text)

        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')

        data = {'type': 'action' if subtype == 'me_message' else 'message',
                'realm': config.realm,
                'channel': '#' + channel['name'],
                'username': user['name'],
                'message': text}
        self.bridge.handle_slack_message(data)

    def handle_user_change(self, user):
        _id = user['id']
        self.users[_id] = user
        
    def handle_channel_change(self, channel):
        _id = channel['id']
        self.channels[_id]['name'] = channel['name']

    def lookup_user(self, _id):
        if _id not in self.users:
            data = self.slack.api_call(
                'users.info',
                user=_id)
            self.users[_id] = data['user']

        return self.users[_id]

    def lookup_channel(self, _id):
        if _id not in self.channels:
            data = self.slack.api_call(
                'channels.info',
                channel=_id)
            if data['ok']:
                self.channels[_id] = data['channel']
                return data['channel']

            data = self.slack.api_call(
                'groups.info',
                channel=_id)
            if data['ok']:
                self.channels[_id] = data['group']
                return data['group']
            
            self.channels[_id] = None
        return self.channels[_id]


class BridgeClient(SelectableInterface):
    def __init__(self, bridge):
        SelectableInterface.__init__(self)
        self.bridge = bridge
        self.connected = False
        self.backoff = 0
        self.reconnect_time = 0
        self.connect()

    def disconnect(self):
        self.recvbuf = b''
        self.sendbuf = b''
        self.sock.close()
        self.connected = False

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(config.bridge)    
        except:
            self.backoff = min(60, self.backoff + (self.backoff//2) + 1)
            self.reconnect_time = time.time() + self.backoff
            print('Error connecting to gateway, backoff %ds' % self.backoff)
            return

        data = json.dumps({'type': 'auth', 'secret': config.bridge_secret, 'realm': config.realm})
        self.recvbuf = b''
        self.sendbuf = data.encode() + b'\r\n'

        self.backoff = 0
        self.connected = True
        print('Connected to gateway')

    def fileno(self):
        return self.sock.fileno()

    def can_read(self):
        return self.connected

    def can_write(self):
        return self.connected and bool(self.sendbuf)
    
    def do_read(self):
        try:
            data = self.sock.recv(1024)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                self.disconnect()
                return
            elif e.errno == errno.EWOULDBLOCK:
                return
            raise
        if not data:
            self.disconnect()
            return
        self.recvbuf += data
        parts = self.recvbuf.split(b'\r\n')
        lines, self.recvbuf = parts[:-1], parts[-1]

        for line in lines:
            msg = json.loads(line.decode())
            if msg['type'] == 'message':
                self.bridge.handle_bridge_message(msg)
            elif msg['type'] == 'action':
                self.bridge.handle_bridge_action(msg)

    def do_write(self):
        try:
            n = self.sock.send(self.sendbuf[:1024])
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                self.disconnect()
                return
            elif e.errno == errno.EWOULDBLOCK:
                return
            raise
        self.sendbuf = self.sendbuf[n:]

    def do_tick(self, now):
        if not self.connected:
            if self.reconnect_time <= now:
                self.reconnecting = True
                self.connect()

class SlackBridge(object):
    def __init__(self):
        self.bridge_client = BridgeClient(self)
        self.slack_client = SlackClient(self)
        self.selectable = (self.bridge_client, self.slack_client)
    
    def run(self):
        while True:
            now = time.time()
            for obj in self.selectable:
                obj.do_tick(now)

            read_objs = (obj for obj in self.selectable if obj.can_read())
            write_objs = (obj for obj in self.selectable if obj.can_write())

            readable, writeable, _ = select(read_objs, write_objs, [], 1)

            for obj in readable:
                obj.do_read()
    
            for obj in writeable:
                obj.do_write()

    def handle_slack_message(self, message):
        data = json.dumps(message)
        self.bridge_client.sendbuf += data.encode() + b'\r\n'
    
    def handle_bridge_message(self, message):
        text = message['message'].replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        def mention_replace(var):
            name = var.group(2)
            for user in self.slack_client.users.values():
                if user['name'] == name.lower():
                    return '%s<@%s>%s' % (var.group(1), user['id'], var.group(3))
            return var.group(0)
        text = bridge_mention_re.sub(mention_replace, text)
        
        self.slack_client.slack.api_call(
            'chat.postMessage',
            channel=message['channel'],
            text=text,
            username=message['username'],
            icon_url=config.avatar_url.replace('$username', message['username']))

    def handle_bridge_action(self, message):
        text = message['message'].replace('<', '&lt;')
        text = text.replace('<', '&gt;')
        def mention_replace(var):
            name = var.group(2)
            for user in self.slack_client.users.values():
                if user['name'] == name.lower():
                    return '%s<@%s>%s' % (var.group(1), user['id'], var.group(3))
            return var.group(0)
        text = bridge_mention_re.sub(mention_replace, text)
        
        self.slack_client.slack.api_call(
            'chat.postMessage',
            channel=message['channel'],
            text='_%s_' % message['message'],
            username=message['username'],
            icon_url=config.avatar_url.replace('$username', message['username']))
