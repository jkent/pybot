# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    def on_message(self, msg):
        if msg['command'] == 'PRIVMSG':
            if msg['trailing'].startswith('!raw '):
                self.client.write(msg['trailing'][5:])

