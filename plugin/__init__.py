# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
import inspect
import sys
import traceback

from interfaces import PluginInterface

__all__ = ['BasePlugin', 'reply', 'trigger']


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
        plugins[name].on_load()
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
        plugins[name].on_unload()
        plugins[name] = sys.modules[module_name].Plugin(client)
        plugins[name].on_load()
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
        plugins[name].on_unload()
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
        if msg['command'] == 'PRIVMSG' and msg['trailing'].startswith('!'):
            trigger = msg['trailing'][1:]
            dispatch_trigger(msg, trigger)


def reply(text):
    frame = inspect.currentframe()
    try:
        back_locals = frame.f_back.f_locals
        client = back_locals['self'].client
        msg = back_locals['msg']
        client.write('PRIVMSG %s :%s' % (msg['reply'], text))
    except:
        raise Exception('reply requires self.client and msg in scope')


#####################
### Trigger system

triggers = []


def trigger(arg=None):
    call = hasattr(arg, '__call__')
    name = arg if not call else None

    def decorate(f):
        trigger = name if name else f.__name__.replace('_', ' ')
        try:
            f._marks.append(trigger)
        except AttributeError:
            f._marks = [trigger]
        return f
    return decorate(arg) if call else decorate


def collect_triggers(plugin):
    for _, f in inspect.getmembers(plugin, inspect.ismethod):
        try:
            for name in f.__func__._marks:
                bisect.insort(triggers, (name, f)) 
        except AttributeError:
            pass


def remove_triggers(plugin):
    triggers[:] = [c for c in triggers if c[1].__self__ != plugin]


def dispatch_trigger(msg, trigger):
    i = bisect.bisect(triggers, (trigger + ' ',)) - 1
    name, f = triggers[i]
    if trigger == name or trigger.startswith(name + ' '):
        argstr = trigger[len(name) + 1:]
        f(msg, argstr)

