# -*- coding: utf-8 -*-
# vim: set ts=4 et

import os
from select import select
from time import time

import reloader

from bot import Bot


class Core(object):
    def __init__(self):
        self.selectable = []
        self.running = False
        self.in_shutdown = False

        self.init_paths()
        reloader.enable(blacklist=['bot', 'client', 'core', 'decorators', 'hook', 'interface', 'message', 'plugin'])

    def init_paths(self):
        self.root = os.path.dirname(os.path.abspath(__file__))
        self.parent = os.path.abspath(os.path.join(self.root, '..'))
        self.plugin_dir = os.path.join(self.root, 'plugins')
        self.data_path = os.path.join(self.parent, 'data')

    def add_bot(self, configfile):
        configfile = os.path.join(self.parent, configfile)
        if not os.path.exists(configfile):
            raise Exception("Config file not found")
        bot = Bot(self, configfile)
        self.selectable.append(bot)

    def run(self):
        self.running = True
        while self.running:
            try:
                self.tick()
            except KeyboardInterrupt:
                self.shutdown('KeyboardInterrupt')
            if self.in_shutdown:
                shutdown = True
                for obj in self.selectable:
                    if obj.connected:
                        shutdown = False
                        break
                if shutdown:
                    self.running = False

    def tick(self):
        timestamp = time()
        for obj in self.selectable:
            obj.do_tick(timestamp)

        read_objs = (obj for obj in self.selectable if obj.can_read())
        write_objs = (obj for obj in self.selectable if obj.can_write())

        readable, writeable, _ = select(read_objs, write_objs, [], 0.25)

        for obj in readable:
            obj.do_read()

        for obj in writeable:
            obj.do_write()

    def shutdown(self, reason=''):
        if self.in_shutdown:
            self.running = False
            return

        self.in_shutdown = True

        for obj in self.selectable:
            if obj.connected and isinstance(obj, Bot):
                obj.hooks.call_event('shutdown', reason)
