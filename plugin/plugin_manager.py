# -*- coding: utf-8 -*-
# vim: set ts=4 et

import time


import core
import plugin
from plugin import *
plugins = plugin.plugins


class Plugin(BasePlugin):
    def trigger(self, msg, args):
        if args[0] == 'list':
            names = ', '.join(plugins.keys())
            self.client.write('PRIVMSG %s :Plugins: %s' % (msg['reply'], names))
        elif args[0] == 'load':
            if plugin.load(args[1], self.client):
                self.client.write('PRIVMSG %s :%s loaded' % (msg['reply'], args[1]))
            else:
                self.client.write('PRIVMSG %s :%s failed to load' % (msg['reply'], args[1]))
        elif args[0] == 'reload':
            if plugin.reload(args[1]):
                self.client.write('PRIVMSG %s :%s reloaded' % (msg['reply'], args[1]))
            else:
                self.client.write('PRIVMSG %s :%s failed to reload' % (msg['reply'], args[1]))
        elif args[0] == 'unload':
            if plugin.unload(args[1]):
                self.client.write('PRIVMSG %s :%s unloaded' % (msg['reply'], args[1]))
            else:
                self.client.write('PRIVMSG %s :%s failed to unload' % (msg['reply'], args[1]))

    def on_message(self, msg):
        if msg['command'] == 'PRIVMSG':
            if msg['trailing'].startswith('!plugin '):
                args = msg['trailing'].split(' ')[1:]
                self.trigger(msg, args)

