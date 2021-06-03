# -*- coding: utf-8 -*-
# vim: set ts=4 et

from textwrap import wrap
from time import time

from . import config
from .client import Client
from .decorators import hook, priority
from .hook import HookManager, TimestampHook
from .plugin import PluginManager


class Bot(Client):
    def __init__(self, core, network):
        self.core = core
        self.network = network

        host = config.config[self.network].get('host')
        port = config.config[self.network].get('port')
        ssl = config.config[self.network].get('ssl', 'false')
        if port == None:
            port = 6697 if ssl else 6667

        Client.__init__(self, (host, port), ssl)
        self.hooks = HookManager(self)
        self.plugins = PluginManager(self)

        self.hooks.install_owner(self)

        self.nick = None
        self.channels = {}
        self.allow_rules = {'*': {'ANY': 1}}
        self.deny_rules = {}

        for plugin in config.autoload_list(self):
            self.plugins.load(plugin)

        self.connect()


    def set_timer(self, fn, timestamp, owner=None):
        hook = TimestampHook(timestamp)
        hook.bind(fn, owner)
        self.hooks.install(hook)
        return hook


    def set_interval(self, fn, seconds, owner=None):
        hook = TimestampHook(time() + seconds, {'repeat': seconds})
        hook.bind(fn, owner)
        self.hooks.install(hook)
        return hook


    def set_timeout(self, fn, seconds, owner=None):
        hook = TimestampHook(time() + seconds)
        hook.bind(fn, owner)
        self.hooks.install(hook)
        return hook


    def do_tick(self, timestamp):
        self.hooks.call_timestamp(timestamp)


    def privmsg(self, target, text):
        wraplen = 510
        wraplen -= 1 + len(self.nick) # ":<nick>"
        wraplen -= 1 + 10 # "!<user>"
        wraplen -= 1 + 63 # "@<host>"
        wraplen -= 9 # " PRIVMSG "
        wraplen -= len(target) # "<target>"
        wraplen -= 2 # " :"
        for line in wrap(text, wraplen):
            self.send('PRIVMSG %s :%s' % (target, line))


    def notice(self, target, text):
        wraplen = 510
        wraplen -= 1 + len(self.nick) # ":<nick>"
        wraplen -= 1 + 10 # "!<user>"
        wraplen -= 1 + 63 # "@<host>"
        wraplen -= 8 # " NOTICE "
        wraplen -= len(target) # "<target>"
        wraplen -= 2 # " :"
        for line in wrap(text, wraplen):
            self.send('NOTICE %s :%s' % (target, line))


    def join(self, channels, keys=None):
        if isinstance(channels, str):
            channels = (channels,)
        channels = list(map(str.lower, channels))
        if channels:
            channel_s = ','.join(channels)
            if keys:
                if isinstance(keys, str):
                    keys = (keys,)
                key_s = ','.join(keys)
                self.send('JOIN %s %s' % (channel_s, key_s))
                pairs = list(zip(channels, keys))
                for item in pairs:
                    self.channels[item[0]] = {'key': item[1], 'joined': False,
                            'nicks': set()}
            else:
                self.send('JOIN %s' % channel_s)
                for channel in channels:
                    self.channels[channel] = {'joined': False, 'nicks': set()}


    def part(self, channels, message=None):
        if type(channels) == str:
            channels = (channels,)
        if channels:
            channels = ','.join(channels)
            if message:
                self.send('PART %s :%s' % (channels, message))
            else:
                self.send('PART %s' % channels)


    @hook
    @priority(0)
    def disconnect_event(self):
        for _, props in list(self.channels.items()):
            props['joined'] = False
            props['nicks'].clear()


    @hook
    @priority(0)
    def shutdown_event(self, reason):
        self.send('QUIT :%s' % reason)
        for name in self.plugins.list():
            self.plugins.unload(name, True)


    @hook
    def _001_command(self, msg):
        self.server = msg.source
        self.nick = msg.param[0]


    @hook
    def _353_command(self, msg):
        channel = msg.param[2].lower()
        if channel in self.channels and self.channels[channel]['joined']:
            #if 'nicks' not in self.channels[channel]:
            #    self.channels[channel]['nicks'] = set()
            nicks = self.channels[channel]['nicks']
            for nick in msg.param[-1].split():
                if nick.startswith(('~', '&', '@', '%', '+')):
                    nicks.add(nick[1:])
                else:
                    nicks.add(nick)


    @hook
    def join_command(self, msg):
        channel = msg.param[0].lower()
        if msg.source == self.nick:
            if channel not in self.channels:
                self.channels[channel] = {}
            self.channels[channel]['name'] = msg.param[0]
            self.channels[channel]['joined'] = True
        elif channel in self.channels:
            self.channels[channel]['nicks'].add(msg.source)


    @hook
    def kick_command(self, msg):
        channel = msg.param[0].lower()
        if msg.param[1] == self.nick:
            if channel in self.channels:
                self.channels[channel]['joined'] = False
                if 'nicks' in self.channels[channel]:
                    self.channels[channel]['nicks'].clear()
        elif channel in self.channels:
            self.channels[channel]['nicks'].remove(msg.source)


    @hook
    def nick_command(self, msg):
        new_nick = msg.param[0].lower()
        if msg.source == self.nick:
            self.nick = new_nick
        for _, props in list(self.channels.items()):
            if 'nicks' in props and msg.source in props['nicks']:
                props['nicks'].remove(msg.source)
                props['nicks'].add(new_nick)


    @hook
    @priority(0)
    def part_command(self, msg):
        channel = msg.param[0].lower()
        if msg.source == self.nick:
            if channel in self.channels:
                self.channels[channel]['joined'] = False
                if 'nicks' in self.channels[channel]:
                    self.channels[channel]['nicks'].clear()
        elif channel in self.channels:
            self.channels[channel]['nicks'].remove(msg.source)


    @hook
    def ping_command(self, msg):
        self.send('PONG :%s' % msg.param[-1])


    @hook
    @priority(0)
    def quit_command(self, msg):
        for _, props in list(self.channels.items()):
            if 'nicks' in props and msg.source in props['nicks']:
                props['nicks'].remove(msg.source)
