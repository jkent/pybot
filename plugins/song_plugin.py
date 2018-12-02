# -*- coding: utf-8 -*-
# vim: set ts=4 et

import random
import re
import os

from plugin import *


class Plugin(BasePlugin):
    @hook
    def privmsg_command(self, msg):
        m = re.match('^!song.*', msg.param[-1], re.I)
        if not m:
            return

        filename = os.path.join(self.bot.core.data_path, 'tunes')
        song_list = open(filename).read().splitlines()
        song = random.choice(song_list)
        msg.reply(song)
