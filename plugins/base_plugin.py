# -*- coding: utf-8 -*-
# vim: set ts=4 et

import time

import config
from plugin import *

BOT_PING_TIME = 120
BOT_PING_TIMEOUT = 60

class Plugin(BasePlugin):
    default_priority = 100

    def __init__(self, *args):
        BasePlugin.__init__(self, *args)
        self.connecting = False
        self.autojoin = config.autojoin
        self.send_ping_hook = None
        self.ping_timeout_hook = None

    def on_unload(self, reloading):
        if not reloading:
            return True

    @hook
    def connect_event(self):
        self.bot.send('NICK %s' % config.nickname)
        self.bot.send('USER %s * 0 :%s' % (config.username, config.realname))

    @hook
    @priority(99)
    def disconnect_event(self):
        if self.bot.core.in_shutdown:
            return
        if not self.autojoin:
            for channel, props in self.bot.channels.items():
                if not props['joined']:
                    continue
                if props.has_key('key'):
                    self.autojoin.append((channel, props['key']))
                else:
                    self.autojoin.append(channel)
        self.schedule_reconnect()

    def schedule_reconnect(self):
        if not self.connecting:
            self.connecting = True
            self.reconnect_attempt = 0

        timeout_period = 60 * min(self.reconnect_attempt, 5)
        self.bot.set_timeout(self, self.timeout, timeout_period)
        self.reconnect_attempt += 1

    def timeout(self):
        if self.bot.connected:
            return

        try:
            self.bot.connect()
        except:
            self.schedule_reconnect()

    @hook
    def error_command(self, msg):
        if 'ban' in msg.param[-1]:
            self.bot.core.shutdown('Shutdown due to ban')

    @hook
    def _001_command(self, msg):
        self.connecting = False
        for channel in self.autojoin:
            if isinstance(channel, tuple):
                self.bot.join(channel[0], channel[1])
            else:
                self.bot.join(channel)
        del self.autojoin[:]

    @hook
    def ping_command(self, msg):
        pass

    @hook
    def line_event(self):
        if self.send_ping_hook:
            self.bot.hooks.uninstall(self.send_ping_hook)
            self.send_ping_hook = None

        if self.ping_timeout_hook:
            self.bot.hooks.uninstall(self.ping_timeout_hook)
            self.ping_timeout_hook = None

        self.send_ping_hook = self.bot.set_timeout(self.send_ping, BOT_PING_TIME)

    def send_ping(self):
        self.send_ping_hook = None
        self.bot.send('PING :%s' % self.bot.server)
        self.ping_timeout_hook = self.bot.set_timeout(self.ping_timeout, BOT_PING_TIMEOUT)

    def ping_timeout(self):
        self.ping_timeout_hook = None
        self.bot.disconnect()

