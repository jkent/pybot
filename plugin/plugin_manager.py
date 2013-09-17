# -*- coding: utf-8 -*-
# vim: set ts=4 et

import plugin
from plugin import *


class Plugin(BasePlugin):
    @trigger
    def plugin_list(self, msg):
        names = ', '.join(plugins.keys())
        msg.reply('Plugins: %s' % names)

    @trigger
    def plugin_load(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name required')
            return

        if plugin.load(name, self.client):
            msg.reply('%s loaded' % name)
        else:
            msg.reply('%s failed to load' % name)

    @trigger
    def plugin_reload(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name required')
            return

        if plugin.reload(name):
            msg.reply('%s reloaded' % name)
        else:
            msg.reply('%s failed to reload' % name)

    @trigger
    def plugin_unload(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name required')
            return

        if plugin.unload(name):
            msg.reply('%s unloaded' % name)
        else:
            msg.reply('%s failed to unload' % name)

