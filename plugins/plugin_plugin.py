# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    @hook
    def list_plugins_trigger(self, msg):
        names = ', '.join(self.bot.plugins.list())
        msg.reply(names)

    @hook
    def load_trigger(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name is required')
            return

        error = self.bot.plugins.load(name)
        if error:
            msg.reply('%s plugin error: %s' % (name, error))
        else:
            msg.reply('%s plugin loaded' % name)

    @hook
    def reload_trigger(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name required')
            return

        error = self.bot.plugins.reload(name)
        if error:
            msg.reply('%s plugin error: %s' % (name, error))
        else:
            msg.reply('%s plugin reloaded' % name)

    @hook
    def unload_trigger(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name is required')
            return

        error = self.bot.plugins.unload(name)
        if error:
            msg.reply('%s plugin error: %s' % (name, error))
        else:
            msg.reply('%s plugin unloaded' % name)

