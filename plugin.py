# -*- coding: utf-8 -*-
# vim: set ts=4 et

import sys
import traceback

from decorators import hook, priority, level

__all__ = ['BasePlugin', 'hook', 'priority', 'level']

PLUGIN_MODULE = '%s_plugin'
PLUGIN_ERROR = '%s plugin: %s'


class BasePlugin(object):
    def __init__(self, bot, name, module):
        self.bot = bot
        self.name = name
        self.module = module

    def on_load(self, reloading):
        pass

    def on_unload(self, reloading):
        pass


class PluginManager(object):
    def __init__(self, bot):
        self.bot = bot
        self.plugins = {}

    def _error(self, name, message, show_traceback=False):
        print(PLUGIN_ERROR % (name, message))
        if show_traceback:
            traceback.print_exc()
        return message

    def _load_module(self, name):
        modname = PLUGIN_MODULE % name
        was_loaded = modname in sys.modules

        self.bot.core.scan_plugins()

        backup_modules = dict(sys.modules)
        try:
            module = __import__(modname, globals(), locals(), ['Plugin'], 0)
        except:
            sys.modules = backup_modules
            return None, self._error(name, 'module load failure', True)

        return module, None

    def _reload_module(self, name):
        module, error = self._load_module(name)
        if error: return None, error

        try:
            try:
                from importlib import reload as reload_func
            except:
                reload_func = reload
            module = reload_func(module)
        except:
            return None, self._error(name, 'module reload failure', True)

        return module, None

    def _unload_module(self, name):
        modname = PLUGIN_MODULE % name
        if modname not in sys.modules:
            return

        if modname in sys.modules:
            del sys.modules[modname]

        return None

    def _load_plugin(self, name, reloading=False):
        module, error = self._load_module(name)
        if error: return None, error

        try:
            plugin = module.Plugin(self.bot, name, module)
        except:
            self._unload_module(name)
            return None, self._error(name, 'init error', True)

        try:
            plugin.on_load(reloading)
        except:
            self._unload_module(name)
            return None, self._error(name, 'on_load error', True)

        try:
            self.bot.hooks.install_owner(plugin)
        except:
            try:
                plugin.on_unload(True)
            except:
                pass
            self._unload_module(name)
            return None, self._error(name, 'hook error', True)

        return plugin, None

    def _unload_plugin(self, plugin, force=False, reloading=False):
        name = plugin.name
        try:
            abort = plugin.on_unload(reloading or force)
        except:
            return self._error(name, 'on_unload error', True)

        if not force and abort:
            return self._error(name, 'not permitted')

        try:
            self.bot.hooks.uninstall_owner(plugin)
        except:
            return self._error(name, 'unhook error', True)

    def load(self, name):
        if name in self.plugins:
            return self._error(name, 'already loaded')

        self.bot.hooks.call_event('plugin loading', name)

        plugin, error = self._load_plugin(name)
        if error: return error

        self.plugins[name] = plugin

        self.bot.hooks.call_event('plugin loaded', name)
        
    def reload(self, name):
        if name not in self.plugins:
            return self._error(name, 'not loaded')

        self.bot.hooks.call_event('plugin reload', name)

        _, error = self._reload_module(name)
        if error: return error

        old_plugin = self.plugins[name]

        new_plugin, error = self._load_plugin(name, True)
        if error: return error

        error = self._unload_plugin(old_plugin, False, True)
        if error:
            self._unload_plugin(new_plugin, True, False)
            return error

        self.plugins[name] = new_plugin

        self.bot.hooks.call_event('plugin reloaded', name)

    def unload(self, name, force=False):
        if name not in self.plugins:
            return self._error(name, 'not loaded')

        self.bot.hooks.call_event('plugin unloading', name)

        plugin = self.plugins[name]
        error = self._unload_plugin(plugin, force, False)
        if error: return error

        del self.plugins[name]
        
        error = self._unload_module(name)
        if error: return error

        self.bot.hooks.call_event('plugin unloaded', name)

    def list(self):
        return list(self.plugins.keys())
