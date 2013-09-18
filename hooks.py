# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
import inspect
from sets import Set

import config
debug = 'hooks' in config.debug

def as_tuple(desc):
    if type(desc) == tuple:
        return desc

    if type(desc) == list:
        return tuple(desc)
    else:
        return (desc,)


class Hooks:
    def __init__(self):
        self.hooks = []

    def add(self, _type, desc, method, priority=100):
        desc = as_tuple(desc)
        if not inspect.ismethod(method):
            raise Exception("Only instance methods may be hooked")
        hook = (_type, desc, priority, method)
        if debug:
            print 'new hook: %s' % repr(hook)
        bisect.insort(self.hooks, hook)

    def collect(self, instance):
        priority = getattr(instance, 'priority', 100)
        for _, method in inspect.getmembers(instance, inspect.ismethod):
            try:
                for _type, desc in method.__func__._hooks:
                    self.add(_type, desc, method, priority)
            except AttributeError:
                pass

    def remove_by_instance(self, instance):
        if debug:
            for hook in (h for h in self.hooks if h[3].__self__ == instance):
                print 'removing hook: %s' % repr(hook)

        self.hooks = [h for h in self.hooks if h[3].__self__ != instance]

    def find(self, _type, desc):
        desc = as_tuple(desc)
        i = bisect.bisect_right(self.hooks, (_type, desc))
        j = bisect.bisect_left(self.hooks, (_type, desc + (None,)))
        return self.hooks[i:j]

    def call(self, hooks, *args):
        for hook in hooks:
            if debug:
                print 'calling hook: %s' % repr(hook)
            method = hook[3]
            nargs = method.__func__.__code__.co_argcount - 1
            method(*args[:nargs])

    def make_decorator(self, _type, make_desc=lambda name:name):
        def factory(*args):
            call = len(args) == 1 and hasattr(args[0], '__call__')
            def decorate(f):
                names = args if args and not call else (f.__name__,)
                hooks = ((_type, as_tuple(make_desc(name))) for name in names)
                try:
                    f._hooks.update(hooks)
                except AttributeError:
                    f._hooks = Set(hooks)
                return f
            return decorate(args[0]) if call else decorate
        return factory


from message import Message

hooks = Hooks()

trigger_max_parts = 0

def make_trigger_desc(name):
    global trigger_max_parts

    name = name.replace('_', ' ')
    parts = tuple(name.split())
    trigger_max_parts = max(trigger_max_parts, len(parts))
    return (len(parts),) + parts
    
event = hooks.make_decorator('event')
command = hooks.make_decorator('command', str.upper)
trigger = hooks.make_decorator('trigger', make_trigger_desc)

def call_event(event, *args):
    event_hooks = hooks.find('event', event)
    hooks.call(event_hooks, *args)
    if event == 'line':
        client = args[0]
        line = args[1]
        msg = Message(line, client)
        call_command(msg.cmd, msg)

def call_command(command, *args):
    command_hooks = hooks.find('command', command)
    hooks.call(command_hooks, *args)
    if command == 'PRIVMSG':
        msg = args[0]
        if msg.param[-1].startswith('!'):
            trigger = msg.param[-1][1:]
            call_trigger(trigger, msg)

def call_trigger(trigger, *args):
    msg = args[0]
    for depth in range(trigger_max_parts, 0, -1):
        parts = tuple(trigger.split(None, depth))
        trigger_hooks = hooks.find('trigger', (depth,) + parts[:depth])
        if not trigger_hooks:
            continue

        targstr = parts[depth] if len(parts) > depth else ''
        targs = (' '.join(parts[:depth]),) + tuple(targstr.split())
        hooks.call(trigger_hooks, msg, targs, targstr)

