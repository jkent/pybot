# -*- coding: utf-8 -*-
# vim: set ts=4 et

import time

import core
import plugin
from plugin import *
plugins = plugin.plugins


class Plugin(BasePlugin):
    @command
    def plugin_list(self, msg, args):
        names = ', '.join(plugins.keys())
        reply('Plugins: %s' % names)

    @command
    def plugin_load(self, msg, args):
        try:
            name = args[0]
        except:
            reply('plugin name required')
            return

        if plugin.load(args[0], self.client):
            reply('%s loaded' % args[0])
        else:
            reply('%s failed to load' % args[0])

    @command
    def plugin_reload(self, msg, args):
        try:
            name = args[0]
        except:
            reply('plugin name required')
            return

        if plugin.reload(args[0]):
            reply('%s reloaded' % args[0])
        else:
            reply('%s failed to reload' % args[0])

    @command
    def plugin_unload(self, msg, args):
        try:
            name = args[0]
        except:
            reply('plugin name required')
            return

        if plugin.unload(args[0]):
            reply('%s unloaded' % args[0])
        else:
            reply('%s failed to unload' % args[0])

