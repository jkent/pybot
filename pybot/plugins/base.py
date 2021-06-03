# -*- coding: utf-8 -*-
# vim: set ts=4 et

from pybot.plugin import *

BOT_PING_TIME = 120
BOT_PING_TIMEOUT = 60


class Plugin(BasePlugin):
    def __init__(self, *args):
        BasePlugin.__init__(self, *args)
        self.connecting = False
        self.send_ping_hook = None
        self.ping_timeout_hook = None


    def on_load(self):
        self.channels = self.config.get('channels', [])


    def on_unload(self, reload):
        if not reload:
            return True


    @hook
    def connect_event(self):
        password = self.config.get('connect_password')
        if password:
            self.bot.send('PASS %s %s %s' % (password, '0210', 'IRC|'))

        nickname = self.config.get('nickname', 'pybot')
        self.bot.send('NICK %s' % nickname)

        username = self.config.get('username', 'pybot')
        realname = self.config.get('realname',
                'Python IRC bot - http://git.io/M1XRlw')
        self.bot.send('USER %s * 0 :%s' % (username, realname))


    @hook
    def disconnect_event(self):
        if self.bot.core.in_shutdown:
            return
        if not self.channels:
            for channel, props in self.bot.channels.items():
                if not props['joined']:
                    continue
                if 'key' in props:
                    self.channels.append((channel, props['key']))
                else:
                    self.channels.append(channel)
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
        password = self.config.get('nickserv_password')
        if password:
            self.bot.privmsg('NickServ', 'identify %s' % (password))
        self.connecting = False
        for channel in self.channels:
            if isinstance(channel, tuple):
                self.bot.join(channel[0], channel[1])
            else:
                self.bot.join(channel)
        del self.channels[:]


    @hook
    def recv_event(self):
        if self.send_ping_hook:
            self.bot.hooks.uninstall(self.send_ping_hook)
            self.send_ping_hook = None

        if self.ping_timeout_hook:
            self.bot.hooks.uninstall(self.ping_timeout_hook)
            self.ping_timeout_hook = None

        self.send_ping_hook = self.bot.set_timeout(self.send_ping,
                BOT_PING_TIME)


    def send_ping(self):
        self.send_ping_hook = None
        self.bot.send('PING :%s' % self.bot.server)
        self.ping_timeout_hook = self.bot.set_timeout(self.ping_timeout,
                BOT_PING_TIMEOUT)


    def ping_timeout(self):
        self.ping_timeout_hook = None
        self.bot.disconnect()
