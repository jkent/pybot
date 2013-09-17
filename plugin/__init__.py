# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
import inspect
import sys
import traceback

from interfaces import PluginInterface

__all__ = ['BasePlugin', 'plugins', 'trigger']


class BasePlugin(PluginInterface):
    def __init__(self, client):
        self.client = client
        collect_triggers(self)


plugins = {}

def load(name, client):
    if name in plugins:
        print "%s is already loaded" % name
        return False

    module_name = "plugin." + name
    modules_backup = dict(sys.modules)
    try:
        module = __import__(module_name, globals(), locals(), ['Plugin'], 0)
        plugins[name] = module.Plugin(client)
        plugins[name].on_load(False)
    except:
        sys.modules = modules_backup
        traceback.print_exc()
        return False

    return True


_reload = reload
def reload(name):
    if name not in plugins:
        print "%s is not loaded" % name
        return False

    module_name = "plugin." + name
    client = plugins[name].client
    try:
        _reload(sys.modules[module_name])
        plugins[name].on_unload(True)
        remove_triggers(plugins[name])
        plugins[name] = sys.modules[module_name].Plugin(client)
        plugins[name].on_load(True)
    except:
        print "error reloading %s" % name
        traceback.print_exc()
        return False

    return True


def unload(name):
    if name not in plugins:
        print "%s is not loaded" % name
        return False

    module_name = "plugin." + name
    try:
        plugins[name].on_unload(False)
        remove_triggers(plugins[name])
        del plugins[name]
        del sys.modules[module_name]
    except:
        print "error unloading %s" % name
        traceback.print_exc()
        return False

    return True


def event(_type, *args):
    for name, plugin in plugins.items():
        try:
            getattr(plugin, 'on_' + _type)(*args)
        except:
            print "error in plugin %s" % name
            traceback.print_exc()

    if _type == 'message':
        msg = args[0]
        if msg.cmd == 'PRIVMSG' and msg.param[-1].startswith('!'):
            trigger = msg.param[-1][1:]
            dispatch_trigger(msg, trigger)


#####################
### Trigger system

from sets import Set

triggers = []
trigger_max_parts = 0


def trigger(*args):
    call = len(args) == 1 and hasattr(args[0], '__call__')
    names = list(args) if not call else []
    def decorate(f):
        if not names:
            name = f.__name__.replace('_', ' ')
            names.append(name)
        try:
            f._triggers.update(names)
        except AttributeError:
            f._triggers = Set(names)
        return f
    return decorate(args[0]) if call else decorate


def collect_triggers(plugin):
    global trigger_max_parts

    priority = getattr(plugin, 'priority', 100)
    for _, m in inspect.getmembers(plugin, inspect.ismethod):
        try:
            for name in m.__func__._triggers:
                parts = tuple(name.split())
                trigger_max_parts = max(trigger_max_parts, len(parts))
                bisect.insort(triggers, (len(parts), parts, priority, m)) 
        except AttributeError:
            pass


def remove_triggers(plugin):
    triggers[:] = [t for t in triggers if t[3].__self__ != plugin]


def dispatch_trigger(msg, trigger):
    for depth in range(trigger_max_parts, 0, -1):
        parts = tuple(trigger.split(None, depth))
        leading = parts[:depth]
        i = bisect.bisect_right(triggers, (depth, leading,)) 
        j = bisect.bisect_left(triggers, (depth, leading + ('',),))
        if i == j:
            continue

        argstr = parts[depth] if len(parts) > depth else ''
        args = (' '.join(leading),) + tuple(argstr.split())
        for _, _, _, m in triggers[i:j]:
            nargs = m.__func__.func_code.co_argcount - 1
            m(*(msg, args, argstr)[:nargs])

