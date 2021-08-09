# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
import inspect
import re
import traceback

from .message import Message


url_re = re.compile(
  '(!)?https?://[^ /]+\.[^ /]+(?:/[^ ]*)?'
)

domain_re = re.compile('https?://(?:www\.)?([^ /]+\.[^ /]+)')

class Hook(object):
    def __init__(self, sort, extra={}):
        self.sort = sort
        self.extra = extra


    def __call__(self, *args):
        if not hasattr(self, 'fn'):
            Exception('attempt to call an unbound hook')
            return

        try:
            return self.fn(*args[:self.nargs])
        except:
            print('%s hook error:' % type(self))
            traceback.print_exc()


    def __lt__(self, other):
        return self.sort < other.sort


    def bind(self, fn, owner=None):
        if owner:
            self.owner = owner
        elif hasattr(fn, '__self__'):
            self.owner = fn.__self__
        else:
            raise Exception('unable to bind hook, no owner!')
        self.fn = fn

        if inspect.ismethod(fn):
            self.nargs = self.fn.__func__.__code__.co_argcount - 1
            self.__func__ = self.fn.__func__
        else:
            self.nargs = self.fn.__code__.co_argcount
            self.__func__ = self.fn

        if not hasattr(self.__func__, '_priority'):
            self.__func__._priority = getattr(self.owner, 'default_priority', 500)

        if not hasattr(self.__func__, '_level'):
            self.__func__._level = getattr(self.owner, 'default_level', 1)


class EventHook(Hook):
    def __init__(self, event):
        Hook.__init__(self, event)


class CommandHook(Hook):
    def __init__(self, command):
        Hook.__init__(self, command.upper())


class TriggerHook(Hook):
    def __init__(self, trigger):
        if type(trigger) == str:
            l = trigger.split()
        else:
            l = trigger
        Hook.__init__(self, (len(l),) + tuple(l))


class TimestampHook(Hook):
    def __init__(self, timestamp, extra={}):
        Hook.__init__(self, timestamp, extra)


class UrlHook(Hook):
    def __init__(self, domain):
        Hook.__init__(self, domain)


class HookManager:
    def __init__(self, bot):
        self.bot = bot
        self.event_hooks = []
        self.command_hooks = []
        self.trigger_hooks = []
        self.timestamp_hooks = []
        self.url_hooks = []


    def install(self, hook):
        if not isinstance(hook, Hook):
            raise Exception('hook is not a Hook instance')

        if not hasattr(hook, 'fn') or not hasattr(hook, 'owner'):
            raise Exception('hook not bound')

        default_priority = getattr(hook.owner, 'default_priority', 100)
        default_level = getattr(hook.owner, 'default_level', 1)
        hook.priority = getattr(hook.fn, '_priority', default_priority)
        hook.level = getattr(hook.fn, '_level', default_level)

        d = {EventHook: self.event_hooks,
             CommandHook: self.command_hooks,
             TriggerHook: self.trigger_hooks,
             TimestampHook: self.timestamp_hooks,
             UrlHook: self.url_hooks}

        l = d.get(type(hook), None)

        if l == None:
            raise Exception('unsupported hook class: %s' % type(hook))

        bisect.insort_right(l, hook)


    def install_owner(self, owner):
        for _, method in inspect.getmembers(owner, inspect.ismethod):
            hooks = getattr(method.__func__, '_hooks', [])
            for hook in hooks:
                hook.bind(method, owner)
                self.install(hook)


    def uninstall(self, hook):
        d = {EventHook: self.event_hooks,
             CommandHook: self.command_hooks,
             TriggerHook: self.trigger_hooks,
             TimestampHook: self.timestamp_hooks,
             UrlHook: self.url_hooks}

        l = d.get(type(hook), [])

        l.remove(hook)


    def uninstall_owner(self, owner):
        for l in [self.event_hooks,
                  self.command_hooks,
                  self.trigger_hooks,
                  self.timestamp_hooks,
                  self.url_hooks]:

            l[:] = (h for h in l if h.owner != owner)


    def find(self, model):
        d = {EventHook: self.event_hooks,
             CommandHook: self.command_hooks,
             TriggerHook: self.trigger_hooks,
             TimestampHook: self.timestamp_hooks,
             UrlHook: self.url_hooks}

        l = d.get(type(model), [])

        if isinstance(model, TimestampHook):
            left = 0
        else:
            left = bisect.bisect_left(l, model)

        right = bisect.bisect_right(l, model)

        hook_seq = l[left:right]
        hook_seq.sort(key=lambda h: -h.fn._priority)
        return hook_seq


    def call(self, hook_seq, *args):
        for hook in hook_seq:
            if isinstance(hook, TimestampHook):
                self.uninstall(hook)
                repeat = hook.extra.get('repeat', None)
                if repeat:
                    hook.sort += repeat
                    self.install(hook)

            if hook(*args):
                return True


    def call_event(self, event, *args):
        hooks = self.find(EventHook(event))
        self.call(hooks, *args)
        if event == 'recv':
            msg = Message(args[0], self.bot)
            self.call_command(msg)


    def call_command(self, msg):
        if msg.cmd in ('NOTICE', 'PRIVMSG'):
            self.apply_permissions(msg)
        if msg.cmd == 'PRIVMSG':
            self.process_privmsg(msg)

        hooks = self.find(CommandHook(msg.cmd))
        self.call(hooks, msg)


    def apply_permissions(self, msg):
        msg.permissions = {}
        for pattern, rules in list(self.bot.allow_rules.items()):
            regex = '^' + re.escape(pattern).replace('\\*', '.*') + '$'
            if not re.match(regex, msg.prefix):
                continue

            for plugin, level in list(rules.items()):
                current_level = msg.permissions.get(plugin, level)
                msg.permissions[plugin] = max(level, current_level)

        for pattern, rules in list(self.bot.deny_rules.items()):
            regex = '^' + re.escape(pattern).replace('\\*', '.*') + '$'
            if not re.match(regex, msg.prefix):
                continue

            for plugin, level in list(rules.items()):
                if plugin == 'ANY':
                    for plugin, current_level in list(msg.permissions.items()):
                        msg.permissions[plugin] = min(level, current_level)
                    continue
                current_level = msg.permissions.get(plugin, level)
                msg.permissions[plugin] = min(level, current_level)


    def process_privmsg(self, msg):
        if msg.trigger:
            self.call_trigger(msg)
        elif msg.channel:
            for match in url_re.finditer(msg.param[1]):
                if match.group(1):
                    continue
                url = match.group(0)
                self.call_url(msg, url)


    def call_trigger(self, msg):
        authorized = True
        num_words = len(msg.trigger.split())
        for depth in range(num_words, 0, -1):
            parts = tuple(msg.trigger.split(None, depth))
            hooks = self.find(TriggerHook(parts[:depth]))

            n = len(hooks)
            hooks[:] = [h for h in hooks if
                        h.fn._level <= msg.permissions.get(h.fn.__self__.name, msg.permissions.get('ANY', 0))]

            if len(hooks) < n:
                authorized = False

            if not hooks:
                pass

            targstr = parts[depth] if len(parts) > depth else ''
            targs = (' '.join(parts[:depth]),) + tuple(targstr.split())
            if self.call(hooks, msg, targs, targstr):
                break

        if not authorized:
            msg.reply("You don't have permission to use that trigger")


    def call_timestamp(self, timestamp):
        hooks = self.find(TimestampHook(timestamp))
        self.call(hooks, timestamp)


    def call_url(self, msg, url):
        match = domain_re.match(url)
        if not match:
            return
        domain = match.group(1).lower()

        hooks = self.find(UrlHook(domain))
        if self.call(hooks, msg, domain, url):
            return True

        hooks = self.find(UrlHook('any'))
        self.call(hooks, msg, domain, url)
