# -*- coding: utf-8 -*-
# vim: set ts=4 et

import random
import re
import os

from plugin import *


class Plugin(BasePlugin):
    @hook(('Song', 'song'))
    def song_trigger(self, msg):
        filename = os.path.join(self.bot.core.data_path, 'songs')
        song_list = open(filename).read().splitlines()
        song = random.choice(song_list)
        msg.reply(song)
