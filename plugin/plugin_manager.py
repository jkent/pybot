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
            reply('Plugins %s' % names)
        elif args[0] == 'load':
            if plugin.load(args[1], self.client):
                reply('%s loaded' % args[1])
            else:
                reply('%s failed to load' % args[1])
        elif args[0] == 'reload':
            if plugin.reload(args[1]):
                reply('%s reloaded' % args[1])
            else:
                reply('%s failed to reload' % args[1])
        elif args[0] == 'unload':
            if plugin.unload(args[1]):
                reply('%s unloaded' % args[1])
            else:
                reply('%s failed to unload' % args[1])

    def on_message(self, msg):
        if msg['command'] == 'PRIVMSG':
            if msg['trailing'].startswith('!plugin '):
                args = msg['trailing'].split(' ')[1:]
                self.trigger(msg, args)

