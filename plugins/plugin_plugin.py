# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    @trigger_hook
    def plugin_list(self, msg):
        names = ', '.join(self.bot.plugins.list())
        msg.reply('Loaded plugins: %s' % names)

    @trigger_hook
    def plugin_load(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name is required')
            return

        error = self.bot.plugins.load(name)
        if error:
            msg.reply('%s plugin load error: %s' % (name, error))
        else:
            msg.reply('%s plugin loaded' % name)

    @trigger_hook
    def plugin_reload(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name required')
            return

        error = self.bot.plugins.reload(name)
        if error:
            msg.reply('%s plugin reload error: %s' % (name, error))
        else:
            msg.reply('%s plugin reloaded' % name)

    @trigger_hook
    def plugin_unload(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name is required')
            return

        error = self.bot.plugins.unload(name)
        if error:
            msg.reply('%s plugin unload error: %s' % (name, error))
        else:
            msg.reply('%s plugin unloaded' % name)

