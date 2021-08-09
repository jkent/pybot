# -*- coding: utf-8 -*-
# vim: set ts=4 et

import importlib
import sys
import traceback
from inspect import signature

import reloader
reloader.enable()

from . import config
from .decorators import hook, level, priority


__all__ = ['BasePlugin', 'hook', 'priority', 'level']


class BasePlugin(object):
    def __init__(self, bot, name, module):
        self.bot = bot
        self.name = name
        self.module = module


    def on_load(self, reload):
        pass


    def on_unload(self, reload):
        pass


    def on_reload(self):
        pass


class PluginManager(object):
    def __init__(self, bot):
        self.bot = bot
        self.plugins = {}


    def _error(self, name, message, show_traceback=False):
        print("plugin '%s': %s" % (name, message))
        if show_traceback:
            traceback.print_exc()
        return message


    def _load_module(self, name):
        was_loaded = name in sys.modules

        backup_modules = dict(sys.modules)
        try:
            module = importlib.import_module('plugins.' + name, '')
        except:
            try:
                module = importlib.import_module('.plugins.' + name, 'pybot')
            except:
                sys.modules = backup_modules
                return None, self._error(name, 'module load failure', True)


        return module, None


    def _reload_module(self, name):
        module, error = self._load_module(name)
        if error: return None, error

        try:
            reloader.reload(module)
        except:
            return None, self._error(name, 'module reload failure', True)

        return module, None


    def _unload_module(self, name):
        if name not in sys.modules:
            return

        if name in sys.modules:
            del sys.modules[name]

        return None


    def _load_plugin(self, name):
        module, error = self._load_module(name)
        if error: return None, error

        try:
            config.load(self.bot.core)
        except:
            # TODO: add error message here
            pass

        try:
            plugin = module.Plugin(self.bot, name, module)
        except:
            self._unload_module(name)
            return None, self._error(name, 'init error', True)

        try:
            self.bot.hooks.install_owner(plugin)
        except:
            try:
                params = signature(plugin.on_unload).parameters
                if len(params) == 0:
                    plugin.on_unload()
                elif len(params) >= 1:
                    plugin.on_unload(True)
            except:
                pass
            self._unload_module(name)
            return None, self._error(name, 'hook error', True)

        return plugin, None


    def _unload_plugin(self, plugin):
        name = plugin.name

        try:
            self.bot.hooks.uninstall_owner(plugin)
        except:
            return self._error(name, 'unhook error', True)

        return None


    def load(self, name):
        if name in self.plugins:
            return self._error(name, 'already loaded')

        self.bot.hooks.call_event('plugin loading', name)

        plugin, error = self._load_plugin(name)
        if error: return error
        plugin.config = config.plugin_options(self.bot, name)

        try:
            params = signature(plugin.on_load).parameters
            if len(params) == 0:
                plugin.on_load()
            elif len(params) >= 1:
                plugin.on_load(False)
        except:
            try:
                params = signature(plugin.on_unload).parameters
                if len(params) == 0:
                    plugin.on_unload()
                elif len(params) >= 1:
                    plugin.on_unload(False)
            except:
                pass
            self._unload_plugin(plugin)
            return self._error(name, 'on_load error', True)

        self.plugins[name] = plugin

        self.bot.hooks.call_event('plugin loaded', name)


    def reload(self, name, force=False):
        if name not in self.plugins:
            return self._error(name, 'not loaded')

        self.bot.hooks.call_event('plugin reloading', name)

        old_plugin = self.plugins[name]
        abort = False
        try:
            abort = bool(old_plugin.on_reload())
        except:
            if not force: return self._error(name, 'on_reload error', True)
        if abort and not force: return self._error(name,
                'plugin prohibits reloading')

        _, error = self._reload_module(name)
        if error: return error

        new_plugin, error = self._load_plugin(name)
        if error: return error
        new_plugin.config = config.plugin_options(self.bot, name)

        error = self._unload_plugin(old_plugin)
        if error: return error

        try:
            params = signature(old_plugin.on_unload).parameters
            if len(params) == 0:
                old_plugin.on_unload()
            elif len(params) >= 1:
                old_plugin.on_unload(True)
        except:
            pass

        try:
            params = signature(new_plugin.on_load).parameters
            if len(params) == 0:
                new_plugin.on_load()
            elif len(params) >= 1:
                new_plugin.on_load(True)
        except:
            try:
                params = signature(new_plugin.on_unload).parameters
                if len(params) == 0:
                    new_plugin.on_unload()
                elif len(params) >= 1:
                    new_plugin.on_unload(False)
            except:
                pass
            self._unload_plugin(new_plugin)
            return self._error(name, 'on_load error', True)

        self.plugins[name] = new_plugin

        self.bot.hooks.call_event('plugin reloaded', name)


    def unload(self, name, force=False):
        if name not in self.plugins:
            return self._error(name, 'not loaded')

        self.bot.hooks.call_event('plugin unloading', name)

        plugin = self.plugins[name]
        abort = False
        try:
            params = signature(plugin.on_unload).parameters
            if len(params) == 0:
                abort = bool(plugin.on_unload())
            elif len(params) >= 1:
                abort = bool(plugin.on_unload(False))
        except:
            if not force: return self._error(name, 'on_unload error', True)
        if abort and not force: return self._error(name,
                'plugin prohibits unloading')

        self._unload_plugin(plugin)

        del self.plugins[name]

        error = self._unload_module(name)
        if error: return error

        self.bot.hooks.call_event('plugin unloaded', name)


    def list(self):
        return list(self.plugins.keys())
