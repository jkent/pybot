# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import BasePlugin


class Plugin(BasePlugin):
    def on_message(self, parts):
        if parts['command'] == 'PRIVMSG' and parts['trailing'] == 'test':
            self.client.write('PRIVMSG #wtf :second test')

