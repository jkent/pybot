# -*- coding: utf-8 -*-
# vim: set ts=4 et

import sys
import traceback

from bot import event_hook, command_hook, trigger_hook
import config
from hook import Hooks

__all__ = ['BasePlugin', 'event_hook', 'command_hook', 'trigger_hook']

debug = 'plugin' in config.debug

PLUGIN_MODULE = 'plugins.%s_plugin'
PLUGIN_ERROR = '%s plugin: %s'


class BasePlugin(object):
    def __init__(self, bot):
        self.bot = bot

    def on_load(self, is_reload):
        self.bot.collect_hooks(self)

    def on_unload(self, is_reload):
        self.bot.remove_hooks(self)


class Plugins(object):
    def __init__(self, bot):
        self.bot = bot
        self.plugins = {}

    def _load_module(self, name):
        modname = PLUGIN_MODULE % name
        sys_modules = dict(sys.modules)
        try:
            module = __import__(modname, globals(), locals(), ['Plugin'], 0)
        except:
            sys.modules = sys_modules
            error = 'load failure'
            print '%s plugin: %s' % (name, error)
            traceback.print_exc()
            return None, error

        try:
            module.refcnt = module.refcnt
        except:
            if debug:
                print '%s plugin: loaded %s module' % (name, modname)
            module.refcnt = 0

        return module, None

    def _reload_module(self, name):
        modname = PLUGIN_MODULE % name
        try:
            module = sys.modules[modname]
        except:
            error = 'module not loaded'
            print PLUGIN_ERROR % (name, error)
            return None, error

        refcnt = module.refcnt
        try:
            reload(module)
            if debug:
                print '%s plugin: reloaded %s module' % (name, modname)
        except:
            error = 'module reload failed'
            print PLUGIN_ERROR % (name, error)
            traceback.print_exc()
            return None, error

        module.refcnt = refcnt
        return module, None        

    def _unload_module(self, name):
        modname = PLUGIN_MODULE % name
        try:
            module = sys.modules[modname]
        except:
            error = 'module not loaded'
            print PLUGIN_ERROR % (name, error)
            return error

        module.refcnt = min(module.refcnt-1, 0)
        if not module.refcnt:
            del sys.modules[modname]
            if debug:
                print '%s plugin: unloaded %s module' % (name, modname)

    def _load(self, module, name, is_reload=False):
        if name in self.plugins:
            error = 'already loaded'
            print PLUGIN_ERROR % (name, error)
            return None, error

        try:
            plugin = module.Plugin(self.bot)
        except:
            error = '__init__ error'
            print PLUGIN_ERROR % (name, error)
            traceback.print_exc()
            return None, error

        try:
            plugin.on_load(is_reload)
        except:
            error = 'on_load error'
            print PLUGIN_ERROR % (name, error)
            traceback.print_exc()
            return None, error

        module.refcnt += 1
        self.plugins[name] = plugin
        return plugin, None

    def _unload(self, name, force=False, is_reload=False):
        if name not in self.plugins:
            error = 'not loaded'
            print PLUGIN_ERROR % (name, error)
            return error

        try:
            plugin = self.plugins[name]
            abort = plugin.on_unload(is_reload or force)
        except:
            error = 'on_unload error'
            print PLUGIN_ERROR % (name, error)
            traceback.print_exc()
            return error

        if not force and abort:
            error = 'not permitted'
            print PLUGIN_ERROR % (name, error)
            return error

        del self.plugins[name]

    def load(self, name):
        if debug:
            print '%s plugin: loading' % name

        module, error = self._load_module(name)
        if error: return error

        plugin, error = self._load(module, name)
        if error: return error
        
        if debug:
            print '%s plugin: loaded' % name

    def unload(self, name, force=False):
        if debug:
            print '%s plugin: unloading' % name

        error = self._unload(name, force)
        if error: return error

        error = self._unload_module(name)
        if error: return error

        if debug:
            print '%s plugin: unloaded' % name

    def reload(self, name):
        if debug:
            print '%s plugin: reloading' % name

        module, error = self._reload_module(name)
        if error: return error

        error = self._unload(name, False, True)
        if error: return error

        plugin, error = self._load(module, name, True)
        if error: return error

        if debug:
            print '%s plugin: reloaded' % name

    def list(self):
        return self.plugins.keys()

