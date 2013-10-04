# -*- coding: utf-8 -*-
# vim: set ts=4 et

import inspect

import config
from client import Client
from hook import Hooks, hook
from message import Message
from plugin import Plugins
from time import time


class Bot(Client):
    priority = 10

    def __init__(self, core):
        self.core = core
        Client.__init__(self, config.host, config.ssl)
        self.hooks = Hooks()
        self.plugins = Plugins(self)

        self.max_trigger = 0
        self.collect_hooks(self)

        for name in config.autoload_plugins:
            self.plugins.load(name)

        self.nick = None

        self.connect()

    def collect_hooks(self, instance):
        priority = getattr(instance, 'priority', 100)
        for _, method in inspect.getmembers(instance, inspect.ismethod):
            try:
                for _type, desc in method.__func__._hooks:
                    if _type == 'command':
                        desc = desc.upper()
                    elif _type == 'trigger':
                        parts = tuple(desc.split())
                        self.max_trigger = max(self.max_trigger, len(parts))
                        desc = (len(parts),) + parts
                    self.hooks.add(_type, desc, method, priority)
            except AttributeError:
                pass

    def remove_hooks(self, instance):
        self.hooks.remove_instance_hooks(instance)

    def call_event(self, event, *args):
        hooks = self.hooks.find('event', event)
        Hooks.call(hooks, *args)
        if event == 'line':
            line = args[0]
            msg = Message(line, self)
            self.call_command(msg.cmd, msg)

    def call_command(self, command, *args):
        hooks = self.hooks.find('command', command.upper())
        Hooks.call(hooks, *args)
        if command == 'PRIVMSG':
            msg = args[0]
            trigger = self.detect_trigger(msg)
            if trigger:
                self.call_trigger(trigger, msg)

    def detect_trigger(self, msg):
        text = msg.param[-1]
        trigger = None

        if config.directed_triggers:
            if msg.channel:
                if text.lower().startswith(self.nick.lower()):
                    nicklen = len(self.nick)
                    if text[nicklen] in [',', ':']:
                        trigger = text[nicklen + 1:]
            else:
                trigger = text
        else:
            if text.startswith('!'):
                trigger = text[1:]

        return trigger

    def call_trigger(self, trigger, *args):
        msg = args[0]
        for depth in range(self.max_trigger, 0, -1):
            parts = tuple(trigger.split(None, depth))
            desc = (depth,) + parts[:depth]
            hooks = self.hooks.find('trigger', desc)
            if not hooks:
                continue

            targstr = parts[depth] if len(parts) > depth else ''
            targs = (' '.join(parts[:depth]),) + tuple(targstr.split())
            Hooks.call(hooks, msg, targs, targstr)

    def set_interval(self, method, seconds):
        desc = time() + seconds
        hook = self.hooks.add('timestamp', desc, method, data=seconds)
        return hook
    
    def set_timeout(self, method, seconds):
        desc = time() + seconds
        hook = self.hooks.add('timestamp', desc, method)
        return hook

    def set_timer(self, method, timestamp):
        if timestamp <= time():
            return
        desc = timestamp
        hook = self.hooks.add('timestamp', desc, method)

    def do_tick(self, timestamp):
        hooks = self.hooks.find('timestamp', 0, timestamp)
        Hooks.call(hooks, timestamp)
        for hook in hooks:
            _, desc, _, _, data = hook
            if data == None:
                self.hooks.remove(hook)
                continue
            desc[0] = desc[0] + data

    def privmsg(self, target, text):
        self.send('PRIVMSG %s :%s' % (target, text))

    def notice(self, target, text):
        self.send('NOTICE %s :%s' % (target, text))

    def join(self, channels, keys=None):
        if type(channels) == str:
            channels = (channels,)
        if channels:
            channels = ','.join(channels)
            if keys:
                keys = ','.join(keys)
                self.send('JOIN %s %s' % (channels, keys))
            else:
                self.send('JOIN %s' % channels)

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
    def shutdown_event(self, reason):
        self.send('QUIT :%s' % reason)
        for name in self.plugins.list():
            self.plugins.unload(name, True)

    @hook
    def _001_command(self, msg):
        self.nick = msg.param[0]

    @hook
    def nick_command(self, msg):
        if msg.nick == self.nick:
            self.nick = msg.param[0]

    @hook
    def ping_command(self, msg):
        self.send('PONG :%s' % msg.param[-1])

