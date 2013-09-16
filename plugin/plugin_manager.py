# -*- coding: utf-8 -*-
# vim: set ts=4 et

import time
import core
import plugin
from plugin import BasePlugin, plugins


class Plugin(BasePlugin):
    def trigger(self, sender, target, args):
        if args[0] == 'list':
            names = ', '.join(plugins.keys())
            self.client.write('PRIVMSG %s :Plugins: %s' % (target, names))
        elif args[0] == 'load':
            if plugin.load(args[1], self.client):
                self.client.write('PRIVMSG %s :%s loaded' % (target, args[1]))
            else:
                self.client.write('PRIVMSG %s :%s failed to load' % (target, args[1]))
        elif args[0] == 'reload':
            if plugin.reload(args[1]):
                self.client.write('PRIVMSG %s :%s reloaded' % (target, args[1]))
            else:
                self.client.write('PRIVMSG %s :%s failed to reload' % (target, args[1]))
        elif args[0] == 'unload':
            if plugin.unload(args[1]):
                self.client.write('PRIVMSG %s :%s unloaded' % (target, args[1]))
            else:
                self.client.write('PRIVMSG %s :%s failed to unload' % (target, args[1]))

    def on_message(self, parts):
        if parts['command'] == 'PRIVMSG':
            sender = parts['nickname']
            recipient = parts['params'][0]
            if recipient.startswith('#'):
                target = recipient
            else:
                target = sender
            if parts['trailing'].startswith('!plugin '):
                args = parts['trailing'].split(' ')[1:]
                self.trigger(sender, target, args)

