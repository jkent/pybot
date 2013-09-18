# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
import inspect
import sys
import traceback

import config
from hooks import hooks, event, command, trigger

__all__ = ['BasePlugin', 'command', 'event', 'plugins', 'trigger']

debug = 'plugins' in config.debug


class BasePlugin(object):
    def __init__(self, client):
        self.client = client

    def on_load(self, reloading):
        hooks.collect(self)

    def on_unload(self, reloading):
        hooks.remove_by_instance(self)
        return True


plugins = {}

def load(name, client):
    if debug:
        print 'plugin load: %s' % name

    if name in plugins:
        print 'plugin "%s" already loaded' % name
        return False

    module_name = 'plugin.' + name
    modules_backup = dict(sys.modules)
    try:
        module = __import__(module_name, globals(), locals(), ['Plugin'], 0)
        plugins[name] = module.Plugin(client)
    except:
        print 'plugin "%s" failed to load' % name
        sys.modules = modules_backup
        traceback.print_exc()
        return False

    try:
        plugins[name].on_load(False)
    except:
        traceback.print_exc()

    if debug:
        print 'plugin loaded: %s' % name

    return True


_reload = reload
def reload(name, force=False):
    if debug:
        print 'plugin reload: %s' % name

    if name not in plugins:
        print 'plugin "%s" not loaded' % name
        return False

    module_name = 'plugin.' + name
    client = plugins[name].client
    try:
        _reload(sys.modules[module_name])
        if not force and not plugins[name].on_unload(True):
            print 'plugin "%s" cannot be reloaded'
            return False
        del plugins[name]
        plugins[name] = sys.modules[module_name].Plugin(client)
        plugins[name].on_load(True)
    except:
        print 'plugin "%s" failed to reload' % name
        traceback.print_exc()
        return False

    if debug:
        print 'plugin reloaded: %s' % name

    return True


def unload(name, force=False):
    if debug:
        print 'plugin unload: %s' % name

    if name not in plugins:
        print 'plugin "%s" not loaded' % name
        return False

    module_name = 'plugin.' + name
    try:
        if not force and not plugins[name].on_unload(False):
            print 'plugin "%s" cannot be removed'
            return False
        del plugins[name]
        del sys.modules[module_name]
    except:
        print 'plugin "%s" failed to unload' % name
        traceback.print_exc()
        return False

    if debug:
        print 'plugin unloaded: %s' % name

    return True

