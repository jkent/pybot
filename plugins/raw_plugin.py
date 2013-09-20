# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    @trigger_hook
    def raw(self, msg, args, argstr):
        self.bot.send(argstr)

