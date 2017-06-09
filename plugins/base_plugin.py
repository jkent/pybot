# -*- coding: utf-8 -*-
# vim: set ts=4 et

import time

from plugin import *

BOT_PING_TIME = 120
BOT_PING_TIMEOUT = 60


class Plugin(BasePlugin):
    def __init__(self, *args):
        BasePlugin.__init__(self, *args)
        self.connecting = False
        self.autojoin = self.config_get('autojoin', '').split()
        self.send_ping_hook = None
        self.ping_timeout_hook = None

    def on_unload(self, reload):
        if not reload:
            return True

    @hook
    def connect_event(self):
        password = self.config_get('connect_password', None)
        if password:
            self.bot.send('PASS %s %s %s' % (password, '0210', 'IRC|'))
        
        nickname = self.config_get('nickname')
        self.bot.send('NICK %s' % nickname)

        username = self.config_get('username')
        realname = self.config_get('realname')
        self.bot.send('USER %s * 0 :%s' % (username, realname))

    @hook
    def disconnect_event(self):
        if self.bot.core.in_shutdown:
            return
        if not self.autojoin:
            for channel, props in self.bot.channels.items():
                if not props['joined']:
                    continue
                if 'key' in props:
                    self.autojoin.append((channel, props['key']))
                else:
                    self.autojoin.append(channel)
        self.schedule_reconnect()

    def schedule_reconnect(self):
        if not self.connecting:
            self.connecting = True
            self.reconnect_attempt = 0

        timeout_period = 60 * min(self.reconnect_attempt, 5)
        self.bot.set_timeout(self.timeout, timeout_period)
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
        password = self.config_get('nickserv_password', None)
        if password:
            self.bot.privmsg('NickServ', 'identify %s' % (password))
        self.connecting = False
        for channel in self.autojoin:
            if isinstance(channel, tuple):
                self.bot.join(channel[0], channel[1])
            else:
                self.bot.join(channel)
        del self.autojoin[:]

    @hook
    def recv_event(self):
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
