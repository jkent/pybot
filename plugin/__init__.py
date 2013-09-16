# -*- coding: utf-8 -*-
# vim: set ts=4 et

import sys
import traceback
from interfaces import PluginInterface


class BasePlugin(PluginInterface):
    def __init__(self, client):
        self.client = client


plugins = {}

def load(name, client):
    global plugins

    if name in plugins:
        print "%s is already loaded" % name

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
    global plugins

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
    global plugins

    if name not in plugins:
        print "%s is not loaded" % name
        return False

    module_name = "plugin." + name
    try:
        plugins[name].on_unload()
        del plugins[name]
        del sys.modules[module_name]
    except:
        print "error unloading %s" % name
        traceback.print_exc()
        return False

    return True


def event(_type, *args):
    global plugins

    for name, plugin in plugins.items():
        try:
            getattr(plugin, 'on_' + _type)(*args)
        except:
            print "error in plugin %s" % name
            traceback.print_exc()
    

