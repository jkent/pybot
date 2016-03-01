# -*- coding: utf-8 -*-
# vim: set ts=4 et

import sys
import traceback

import config
from hook import Hooks, hook, priority

__all__ = ['BasePlugin', 'hook', 'priority']

debug = 'plugin' in config.debug

PLUGIN_MODULE = 'plugins.%s_plugin'
PLUGIN_ERROR = '%s plugin: %s'
PLUGIN_DEBUG = '%s plugin: %s'


class BasePlugin(object):
    def __init__(self, bot):
        self.bot = bot

    def on_load(self, reloading):
        pass

    def on_unload(self, reloading):
        pass


class Plugins(object):
    def __init__(self, bot):
        self.bot = bot
        self.plugins = {}

    def _error(self, name, message, show_traceback=False):
        print PLUGIN_ERROR % (name, message)
        if show_traceback:
            traceback.print_exc()
        return message

    def _load_module(self, name):
        modname = PLUGIN_MODULE % name
        was_loaded = modname in sys.modules

        backup_modules = dict(sys.modules)
        try:
            module = __import__(modname, globals(), locals(), ['Plugin'], 0)
        except:
            sys.modules = backup_modules
            return None, self._error(name, 'module load failure', True)

        if debug and not was_loaded:
            print PLUGIN_DEBUG % (name, 'loaded module')

        return module, None

    def _reload_module(self, name):
        modname = PLUGIN_MODULE % name
        module, error = self._load_module(name)
        if error: return None, error

        try:
            reload(module)
        except:
            return None, self._error(name, 'module reload failure', True)

        if debug:
            print PLUGIN_DEBUG % (name, 'reloaded module')

        return module, None

    def _unload_module(self, name):
        modname = PLUGIN_MODULE % name
        if modname not in sys.modules:
            return

        if modname in sys.modules:
            del sys.modules['plugins'].__dict__['%s_plugin' % name]
            del sys.modules[modname]

            if debug:
                print PLUGIN_DEBUG % (name, 'unloaded module')

        return None

    def _load_plugin(self, name, reloading=False):
        module, error = self._load_module(name)
        if error: return None, error

        try:
            plugin = module.Plugin(self.bot)
        except:
            self._unload_module(name)
            return None, self._error(name, 'init error', True)

        try:
            plugin.on_load(reloading)
        except:
            self._unload_module(name)
            return None, self._error(name, 'on_load error', True)

        try:
            self.bot.install_hooks(plugin)
        except:
            try:
                plugin.on_unload(True)
            except:
                pass
            self._unload_module(name)
            return None, self._error(name, 'hook error', True)

        plugin._module = module
        plugin._name = name
        return plugin, None

    def _unload_plugin(self, plugin, force=False, reloading=False):
        name = plugin._name
        module = plugin._module
        try:
            abort = plugin.on_unload(reloading or force)
        except:
            return self._error(name, 'on_unload error', True)

        if not force and abort:
            return self._error(name, 'not permitted')

        try:
            self.bot.uninstall_hooks(plugin)
        except:
            return self._error(name, 'unhook error', True)

    def load(self, name):
        if debug:
            print PLUGIN_DEBUG % (name, 'loading')

        if name in self.plugins:
            return self._error(name, 'already loaded')

        plugin, error = self._load_plugin(name)
        if error: return error

        self.plugins[name] = plugin
        
        if debug:
            print PLUGIN_DEBUG % (name, 'loaded')

    def reload(self, name):
        if debug:
            print PLUGIN_DEBUG % (name, 'reloading')

        if name not in self.plugins:
            return self._error(name, 'not loaded')

        module, error = self._reload_module(name)
        if error: return error

        old_plugin = self.plugins[name]

        new_plugin, error = self._load_plugin(name, True)
        if error: return error

        error = self._unload_plugin(old_plugin, False, True)
        if error:
            self._unload_plugin(new_plugin, True, False)
            return error

        self.plugins[name] = new_plugin

        if debug:
            print PLUGIN_DEBUG % (name, 'reloaded')

    def unload(self, name, force=False):
        if debug:
            print PLUGIN_DEBUG % (name, 'unloading')

        if name not in self.plugins:
            return self._error(name, 'not loaded')

        plugin = self.plugins[name]
        error = self._unload_plugin(plugin, force, False)
        if error: return error

        del self.plugins[name]
        
        error = self._unload_module(name)
        if error: return error

        if debug:
            print PLUGIN_DEBUG % (name, 'unloaded')

    def list(self):
        return self.plugins.keys()

