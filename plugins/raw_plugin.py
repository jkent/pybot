# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    @hook
    def raw_trigger(self, msg, args, argstr):
        self.bot.send(argstr)

