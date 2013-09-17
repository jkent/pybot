# -*- coding: utf-8 -*-
# vim: set ts=4 et

import time

import config
import core
from plugin import BasePlugin


class Plugin(BasePlugin):
    priority = 5

    def __init__(self, *args):
        BasePlugin.__init__(self, *args)
        self.connected = False

    def on_connect(self):
        self.connected = True
        self.client.send('NICK %s' % config.nickname)
        self.client.send('USER %s * 0 :%s' % (config.username, config.realname))

    def on_disconnect(self):
        self.connected = False
        try:
            self.client.connect()
        except:
            self.reconnect_attempt = 0
            self.schedule_reconnect()

    def schedule_reconnect(self):
        self.reconnect_attempt += 1
        self.next_attempt = time.time() + (60 * min(self.reconnect_attempt, 5))

    def on_tick(self, time_now):
        if not self.connected and time_now > self.next_attempt:
            try:
                self.client.connect()
            except:
                self.schedule_reconnect()

    def on_message(self, msg):
        if msg.cmd == 'PING':
            self.client.send('PONG :%s' % msg.param[-1])
        elif msg.cmd == '001':
            for channel in config.autojoin:
                self.client.send('JOIN %s' % channel)

