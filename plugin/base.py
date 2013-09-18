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
        self.connecting = False

    def on_unload(self, reloading):
        if not reloading:
            return False
        return BasePlugin.on_unload(self, reloading)

    @event
    def connect(self):
        self.client.send('NICK %s' % config.nickname)
        self.client.send('USER %s * 0 :%s' % (config.username, config.realname))

    @event
    def disconnect(self):
        self.schedule_reconnect()

    def schedule_reconnect(self):
        if not self.connecting:
            self.connecting = True
            self.reconnect_attempt = 0

        self.next_attempt = time.time() + 60 * min(self.reconnect_attempt, 5)
        self.reconnect_attempt += 1

    @event
    def tick(self, time_now):
        if self.client.connected:
            return

        if time_now > self.next_attempt:
            try:
                self.client.connect()
            except:
                self.schedule_reconnect()

    @command('error')
    def cmd_error(self, msg):
        if 'ban' in msg.param[-1]:
            core.shutdown()

    @command('ping')
    def cmd_ping(self, msg):
        self.client.send('PONG :%s' % msg.param[-1])

    @command('001')
    def cmd_001(self, msg):
        self.connecting = False
        for channel in config.autojoin:
            self.client.send('JOIN %s' % channel)

