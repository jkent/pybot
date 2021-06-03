# -*- coding: utf-8 -*-
# vim: set ts=4 et

from pybot.plugin import *
from pybot import config


class Plugin(BasePlugin):
    default_level = 1000


    @hook
    def config_reload_trigger(self, msg, args, argstr):
        config.load(self.bot.core)
        msg.reply('Configuration reloaded')
