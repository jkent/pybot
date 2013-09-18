# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
import inspect
import sys
import traceback

import hooks
from hooks import event, command, trigger
from interfaces import PluginInterface

__all__ = ['BasePlugin', 'command', 'event', 'plugins', 'trigger']


class BasePlugin(PluginInterface):
    def __init__(self, client):
        self.client = client
        hooks.collect_hooks(self)


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
        hooks.remove_instance_hooks(plugins[name])
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
        hooks.remove_instance_hooks(plugins[name])
        del plugins[name]
        del sys.modules[module_name]
    except:
        print "error unloading %s" % name
        traceback.print_exc()
        return False

    return True

