# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import BasePlugin


class Plugin(BasePlugin):
    def trigger(self, sender, target, args):
        self.client.write(' '.join(args))

    def on_message(self, parts):
        if parts['command'] == 'PRIVMSG':
            sender = parts['nickname']
            recipient = parts['params'][0]
            if recipient.startswith('#'):
                target = recipient
            else:
                target = sender
            if parts['trailing'].startswith('!ss '):
                args = parts['trailing'].split(' ')[1:]
                self.trigger(sender, target, args)

