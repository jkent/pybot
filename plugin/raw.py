# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    @command
    def raw(self, msg, argstr):
        self.client.write(argstr)

