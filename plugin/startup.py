# -*- coding: utf-8 -*-
# vim: set ts=4 et

import time

import config
import core
from plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self, *args):
        BasePlugin.__init__(self, *args)
        self.connected = False

    def on_connect(self):
        self.connected = True
        self.client.write('NICK %s' % config.nickname)
        self.client.write('USER %s * 0 :%s' % (config.username, config.realname))

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

    def on_message(self, parts):
        if parts['command'] == 'PING':
            self.client.write('PONG :%s' % parts['trailing'])
        elif parts['command'] == '001':
            for channel in config.autojoin:
                self.client.write('JOIN %s' % channel)

