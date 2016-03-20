# -*- coding: utf-8 -*-
# vim: set ts=4 et

import inspect
import re

import config
from client import Client
from hook import Hooks, hook, priority
from message import Message
from plugin import Plugins
from time import time

url_re = re.compile(
  'https?://[^ /]+\.[^ /]+(?:/[^ ]*)?'  +
  '|'                                   +
  '(?<![^ ])[^ /]+\.[^ /]+/[^ ]*'
)

domain_re = re.compile('https?://(?:www\.)?([^ /]+\.[^ /]+)')


class Bot(Client):
    default_priority = 100

    def __init__(self, core):
        self.core = core
        Client.__init__(self, config.host, config.ssl)
        self.hooks = Hooks()
        self.plugins = Plugins(self)

        self.max_trigger = 0
        self.install_hooks(self)

        self.nick = None
        self.channels = {}
        self.allow_rules = {'*': {'ANY': 1}, config.superuser: {'ANY': 1000}}
        self.deny_rules = {}
        self._name = '_bot'

        for name in config.autoload_plugins:
            self.plugins.load(name)

        self.connect()

    def install_hook(self, owner, hook):
        hooks = owner._hooks = getattr(owner, '_hooks', [])
        data = hook[4]
        data['uninstall'] = lambda hook: hooks.remove(hook)
        self.hooks.install(hook)
        hooks.append(hook)

    def uninstall_hook(self, hook):
        self.hooks.uninstall(hook)

    def install_hooks(self, owner):
        default_priority = getattr(owner, 'default_priority', 500)
        default_level = getattr(owner, 'default_level', 1)
        for _, method in inspect.getmembers(owner, inspect.ismethod):
            try:
                for _type, desc in method.__func__._hooks:
                    if _type == 'command':
                        desc = desc.upper()
                    elif _type == 'trigger':
                        parts = tuple(desc.split())
                        self.max_trigger = max(self.max_trigger, len(parts))
                        desc = (len(parts),) + parts
                        try:
                            method.__func__._level
                        except AttributeError:
                            method.__func__._level = default_level
                    try:
                        priority = method.__func__._priority
                    except AttributeError:
                        priority = default_priority
                    hook = self.hooks.create(method, _type, desc, priority)
                    self.install_hook(owner, hook)
            except AttributeError:
                pass

    def uninstall_hooks(self, owner):
        try:
            hooks = owner._hooks[:]
        except AttributeError:
            return

        for hook in hooks:
            self.uninstall_hook(hook)

    def call_event(self, event, *args):
        hooks = self.hooks.find('event', event)
        Hooks.call(hooks, *args)
        if event == 'line':
            line = args[0]
            msg = Message(line, self)
            self.call_command(msg.cmd, msg)

    def call_command(self, command, *args):
        if command in ('NOTICE', 'PRIVMSG'):
            self.apply_permissions(args[0])
        if command == 'PRIVMSG':
            self.process_privmsg(args[0])
        hooks = self.hooks.find('command', command.upper())
        Hooks.call(hooks, *args)

    def apply_permissions(self, msg):
        msg.permissions = {}
        for pattern, rules in self.allow_rules.items():
            regex = '^' + re.escape(pattern).replace('\\*', '.*') + '$'
            if not re.match(regex, msg.prefix):
                continue

            for plugin, level in rules.items():
                current_level = msg.permissions.get(plugin, level)
                msg.permissions[plugin] = max(level, current_level)

        for pattern, rules in self.deny_rules.items():
            regex = '^' + re.escape(pattern).replace('\\*', '.*') + '$'
            if not re.match(regex, msg.prefix):
                continue

            for plugin, level in rules.items():
                if plugin == 'ANY':
                    for plugin, current_level in msg.permissions.items():
                        msg.permissions[plugin] = min(level, current_level)
                    continue
                current_level = msg.permissions.get(plugin, level)
                msg.permissions[plugin] = min(level, current_level)

    def process_privmsg(self, msg):
        trigger = self.detect_trigger(msg)
        if trigger:
            msg.trigger = True
            self.call_trigger(trigger, msg)
        elif msg.channel:
            for match in url_re.finditer(msg.param[1]):
                url = match.group(0)
                if not url.startswith(('http:', 'https:')):
                    url = 'http://' + url
                self.do_url(msg, url)

    def detect_trigger(self, msg):
        text = msg.param[-1]
        trigger = None

        if config.directed_triggers:
            if msg.channel:
                if text.lower().startswith(self.nick.lower()):
                    nicklen = len(self.nick)
                    if len(text) > nicklen and text[nicklen] in [',', ':']:
                        trigger = text[nicklen + 1:]
            else:
                trigger = text
        else:
            if text.startswith('!'):
                trigger = text[1:]

        return trigger

    def call_trigger(self, trigger, *args):
        authorized = True
        msg = args[0]
        for depth in range(self.max_trigger, 0, -1):
            parts = tuple(trigger.split(None, depth))
            desc = (depth,) + parts[:depth]
            hooks = self.hooks.find('trigger', desc)

            if not hooks:
                continue

            for i, hook in enumerate(hooks):
                plugin = hook[3].im_self._name
                level = hook[3]._level
                if level > max(msg.permissions.get('ANY', 0), msg.permissions.get(plugin, 0)):
                    del hooks[i]
                    authorized = False

            if not hooks:
                continue

            targstr = parts[depth] if len(parts) > depth else u''
            targs = (' '.join(parts[:depth]),) + tuple(targstr.split())
            if Hooks.call(hooks, msg, targs, targstr):
                break

        if not authorized:
            msg.reply("You don't have permission to use that trigger")

    def set_interval(self, owner, fn, seconds):
        desc = time() + seconds
        data = {'seconds': seconds}
        hook = self.hooks.create(fn, 'timestamp', desc, data=data)
        self.install_hook(owner, hook)
        return hook

    def set_timeout(self, owner, fn, seconds):
        desc = time() + seconds
        hook = self.hooks.create(fn, 'timestamp', desc)
        self.install_hook(owner, hook)
        return hook

    def set_timer(self, owner, fn, timestamp):
        if timestamp <= time():
            return None
        desc = timestamp
        hook = self.hooks.create(fn, 'timestamp', desc)
        self.install_hook(owner, hook)
        return hook

    def do_tick(self, timestamp):
        hooks = self.hooks.find('timestamp', 0, timestamp)
        Hooks.call(hooks, timestamp)
        for hook in hooks:
            _, desc, _, _, data = hook
            seconds = data.get('seconds', None)
            if seconds:
                with self.hooks.modify(hook):
                    desc[0] += seconds
            else:
                self.hooks.uninstall(hook)

    def do_url(self, msg, url):
        match = domain_re.match(url)
        if not match:
            return
        domain = match.group(1)

        hooks = self.hooks.find('url', domain)
        hooks.extend(self.hooks.find('url', domain.replace('.', ' ')))
        if Hooks.call(hooks, msg, domain, url):
            return

        hooks = self.hooks.find('url', 'any')
        Hooks.call(hooks, msg, domain, url)

    def privmsg(self, target, text):
        self.send('PRIVMSG %s :%s' % (target, text))

    def notice(self, target, text):
        self.send('NOTICE %s :%s' % (target, text))

    def join(self, channels, keys=None):
        if isinstance(channels, str):
            channels = (channels,)
        if channels:
            channel_s = ','.join(channels)
            if keys:
                if isinstance(keys, str):
                    keys = (keys,)
                key_s = ','.join(keys)
                self.send('JOIN %s %s' % (channel_s, key_s))
                pairs = zip(channels, keys)
                for item in pairs:
                    self.channels[item[0]] = {'key': item[1], 'joined': False, 'nicks': set()}
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
    def disconnect_event(self):
        for _, props in self.channels.items():
            props['joined'] = False
            props['nicks'].clear()

    @hook
    @priority(1000)
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
        channel = msg.param[2]
        if self.channels.has_key(channel) and self.channels[channel]['joined']:
            nicks = self.channels[channel]['nicks']
            for nick in msg.param[-1].split():
                if nick.startswith(('~', '&', '@', '%', '+')):
                    nicks.add(nick[1:])
                else:
                    nicks.add(nick)

    @hook
    def join_command(self, msg):
        channel = msg.param[0]
        if msg.source == self.nick:
            if not self.channels.has_key(channel):
                self.channels[channel] = {}
            self.channels[channel]['joined'] = True
        elif self.channels.has_key(channel):
            self.channels[channel]['nicks'].add(msg.source)

    @hook
    def kick_command(self, msg):
        channel = msg.param[0]
        if msg.param[1] == self.nick:
            if self.channels.has_key(channel):
                self.channels[channel]['joined'] = False
                if self.channels[channel].has_key('nicks'):
                    self.channels[channel]['nicks'].clear()
        elif self.channels.has_key(channel):
            self.channels[channel]['nicks'].remove(msg.source)

    @hook
    def nick_command(self, msg):
        new_nick = msg.param[0]
        if msg.source == self.nick:
            self.nick = new_nick
        for _, props in self.channels.items():
            if props.has_key('nicks') and msg.source in props['nicks']:
                props['nicks'].remove(msg.source)
                props['nicks'].add(new_nick)

    @hook
    @priority(1000)
    def part_command(self, msg):
        channel = msg.param[0]
        if msg.source == self.nick:
            if self.channels.has_key(channel):
                self.channels[channel]['joined'] = False
                if self.channels[channel].has_key('nicks'):
                    self.channels[channel]['nicks'].clear()
        elif self.channels.has_key(channel):
            self.channels[channel]['nicks'].remove(msg.source)

    @hook
    def ping_command(self, msg):
        self.send('PONG :%s' % msg.param[-1])

    @hook
    @priority(1000)
    def quit_command(self, msg):
        for _, props in self.channels.items():
            if props.has_key('nicks') and msg.source in props['nicks']:
                props['nicks'].remove(msg.source)

