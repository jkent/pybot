# -*- coding: utf-8 -*-
# vim: set ts=4 et

import time

import config
import core
from plugin import *


class Plugin(BasePlugin):
    priority = 5

    def __init__(self, *args):
        BasePlugin.__init__(self, *args)
        self.connected = False

    def on_unload(self, reloading):
        if not reloading:
            return False
        return BasePlugin.on_unload(self, reloading)

    @event
    def connect(self):
        self.connected = True
        self.client.send('NICK %s' % config.nickname)
        self.client.send('USER %s * 0 :%s' % (config.username, config.realname))

    @event
    def disconnect(self):
        self.connected = False
        try:
            self.client.connect()
        except:
            self.reconnect_attempt = 0
            self.schedule_reconnect()

    def schedule_reconnect(self):
        self.reconnect_attempt += 1
        self.next_attempt = time.time() + (60 * min(self.reconnect_attempt, 5))

    @event
    def tick(self, time_now):
        if not self.connected and time_now > self.next_attempt:
            try:
                self.client.connect()
            except:
                self.schedule_reconnect()

    @command('PING')
    def cmd_ping(self, msg):
        self.client.send('PONG :%s' % msg.param[-1])

    @command('001')
    def cmd_001(self, msg):
        for channel in config.autojoin:
            self.client.send('JOIN %s' % channel)

