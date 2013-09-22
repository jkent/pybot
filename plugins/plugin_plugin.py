# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    @hook
    def plugin_list_trigger(self, msg):
        names = ', '.join(self.bot.plugins.list())
        msg.reply('Loaded plugins: %s' % names)

    @hook
    def plugin_load_trigger(self, msg, args):
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

    @hook
    def plugin_reload_trigger(self, msg, args):
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

    @hook
    def plugin_unload_trigger(self, msg, args):
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

