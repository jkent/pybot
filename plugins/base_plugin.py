# -*- coding: utf-8 -*-
# vim: set ts=4 et

import time

import config
from plugin import *


class Plugin(BasePlugin):
    priority = 5

    def __init__(self, *args):
        BasePlugin.__init__(self, *args)
        self.connecting = False

    def on_unload(self, reloading):
        if not reloading:
            return True
        return BasePlugin.on_unload(self, reloading)

    @event_hook
    def connect(self):
        self.bot.send('NICK %s' % config.nickname)
        self.bot.send('USER %s * 0 :%s' % (config.username, config.realname))

    @event_hook
    def disconnect(self):
        self.schedule_reconnect()

    def schedule_reconnect(self):
        if not self.connecting:
            self.connecting = True
            self.reconnect_attempt = 0

        self.next_attempt = time.time() + 60 * min(self.reconnect_attempt, 5)
        self.reconnect_attempt += 1

    @event_hook
    def tick(self, time_now):
        if self.bot.connected:
            return

        if time_now > self.next_attempt:
            try:
                self.bot.connect()
            except:
                self.schedule_reconnect()

    @command_hook
    def error(self, msg):
        if 'ban' in msg.param[-1]:
            self.bot.core.shutdown('Shutdown due to ban')

    @command_hook('001')
    def _001(self, msg):
        self.connecting = False
        self.bot.join(config.autojoin)

