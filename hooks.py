# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
import inspect
from sets import Set
import pprint

from message import Message


hooks = []
trigger_max_parts = 0

def add_hook(_type, desc, method, priority=100):
    if type(desc) != tuple:
        if type(desc) == list:
            desc = tuple(desc)
        else:
            desc = (desc,)
    if not inspect.ismethod(method):
        raise Exception("Only instance methods may be hooked")

    hook = (_type, desc, priority, method)
    bisect.insort(hooks, hook)

def remove_instance_hooks(instance):
    hooks[:] = [hook for hook in hooks if hook[2].__self__ != instance]

def find_hooks(_type, desc):
    if type(desc) != tuple:
        if type(desc) == list:
            desc = tuple(desc)
        else:
            desc = (desc,)

    i = bisect.bisect_right(hooks, (_type, desc))
    j = bisect.bisect_left(hooks, (_type, desc + (None,)))
    return hooks[i:j]

def call_hooks(hooks, *args):
    for _, _, _, m in hooks:
        nargs = m.__func__.__code__.co_argcount - 1
        m(*args[:nargs])

def add_event(event, method, priority=100):
    add_event('event', event, priority, method)

def add_command(command, method, priority=100):
    add_hook('command', command, priority, method)

def add_trigger(trigger, method, priority=100):
    global trigger_max_parts
    parts = tuple(trigger.split())
    trigger_max_parts = max(trigger_max_parts, len(parts))
    add_hook('trigger', (len(parts),) + parts, priority, method)

def call_event(event, *args):
    hooks = find_hooks('event', event)
    call_hooks(hooks, *args)
    if event == 'line':
        client = args[0]
        line = args[1]
        msg = Message(line, client)
        call_command(msg.cmd, msg)

def call_command(command, *args):
    hooks = find_hooks('command', command)
    call_hooks(hooks, *args)
    if command == 'PRIVMSG':
        msg = args[0]
        if msg.param[-1].startswith('!'):
            trigger = msg.param[-1][1:]
            call_trigger(trigger, msg)

def call_trigger(trigger, *args):
    msg = args[0]
    for depth in range(trigger_max_parts, 0, -1):
        parts = tuple(trigger.split(None, depth))
        hooks = find_hooks('trigger', (depth,) + parts[:depth])
        if not hooks:
            continue

        targstr = parts[depth] if len(parts) > depth else ''
        targs = (' '.join(parts[:depth]),) + tuple(targstr.split())
        call_hooks(hooks, msg, targs, targstr)

def collect_hooks(instance):
    priority = getattr(instance, 'priority', 100)
    for _, m in inspect.getmembers(instance, inspect.ismethod):
        try:
            for hook in m.__func__._hooks:
                add_hook(hook[0], hook[1], m, priority)
        except AttributeError:
            pass

def event(*args):
    call = len(args) == 1 and hasattr(args[0], '__call__')
    events = args if not call else []
    def decorate(f):
        if not events:
            events.append(f.__name__)
        hooks = (('event', event) for event in events)
        try:
            f._hooks.update(hooks)
        except AttributeError:
            f._hooks = Set(hooks)
        return f
    return decorate(args[0]) if call else decorate

def command(*args):
    call = len(args) == 1 and hasattr(args[0], '__call__')
    commands = args if not call else []
    def decorate(f):
        if not commands:
            commands.append(f.__name__.upper())
        hooks = (('command', command) for command in commands)
        try:
            f._hooks.update(hooks)
        except AttributeError:
            f._hooks = Set(hooks)
        return f
    return decorate(args[0]) if call else decorate

def trigger(*args):
    call = len(args) == 1 and hasattr(args[0], '__call__')
    triggers = args if not call else []
    def decorate(f):
        global trigger_max_parts
        if not triggers:
            triggers.append(f.__name__.replace('_', ' '))
        hooks = []
        for trigger in triggers:
            parts = tuple(trigger.split())
            trigger_max_parts = max(trigger_max_parts, len(parts))
            hooks.append(('trigger', (len(parts),) + parts))
        try:
            f._hooks.update(hooks)
        except AttributeError:
            f._hooks = Set(hooks)
        return f
    return decorate(args[0]) if call else decorate

