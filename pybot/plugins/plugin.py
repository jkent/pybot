# -*- coding: utf-8 -*-
# vim: set ts=4 et

from pybot.plugin import *


class Plugin(BasePlugin):
    default_level = 900

    @hook
    def plugin_list_trigger(self, msg):
        names = ', '.join(self.bot.plugins.list())
        msg.reply(names)

    @hook
    def plugin_load_trigger(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name is required')
            return

        error = self.bot.plugins.load(name)
        if error:
            msg.reply("'%s' plugin error: %s" % (name, error))
        else:
            msg.reply("'%s' plugin loaded" % name)

    @hook
    def plugin_reload_trigger(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name required')
            return

        force = name.startswith('!')
        if force: name = name[1:]

        error = self.bot.plugins.reload(name, force)
        if error:
            msg.reply("'%s' plugin error: %s" % (name, error))
        else:
            msg.reply("'%s' plugin reloaded" % name)

    @hook
    def plugin_unload_trigger(self, msg, args):
        try:
            name = args[1]
        except:
            msg.reply('plugin name is required')
            return

        force = name.startswith('!')
        if force: name = name[1:]

        error = self.bot.plugins.unload(name, force)
        if error:
            msg.reply("'%s' plugin error: %s" % (name, error))
        else:
            msg.reply("'%s' plugin unloaded" % name)
