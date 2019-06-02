# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    default_level = 1000

    @hook
    def eval_trigger(self, msg, args, argstr):
        try:
            result = eval(argstr, globals(), locals())
        except Exception as e:
            result = e
        msg.reply(repr(result))
