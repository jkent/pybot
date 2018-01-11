# -*- coding: utf-8 -*-
# vim: set ts=4 et

from select import select
from time import time
import os
import sys

from bot import Bot


class Core(object):
    def __init__(self):
        self.selectable = []
        self.running = False
        self.in_shutdown = False

        self.init_paths()
        self.scan_plugins()

    def init_paths(self):
        self.root = os.path.dirname(os.path.abspath(__file__))
        self.parent = os.path.abspath(os.path.join(self.root, '..'))
        lib_path = os.path.abspath(os.path.join(self.parent, 'lib'))
        sys.path.insert(1, lib_path)

        self.plugin_dir = os.path.join(self.parent, 'plugins')
        sys.path.append(self.plugin_dir)

        self.data_path = os.path.join(self.parent, 'data')

    def scan_plugins(self):
        for dirname in sys.path[:]:
            if dirname.startswith(os.path.join(self.plugin_dir, '')):
                sys.path.remove(dirname)

        def add_path(path):
            if path not in sys.path:
                sys.path.append(path)

        for root, dirs, files in os.walk(self.plugin_dir):
            for filename in files:
                if filename.endswith('_plugin.py'):
                    add_path(root)
                    break
            if root.endswith('_plugin'):
                lib = os.path.join(root, 'lib')
                if not os.path.exists(lib): continue
                for modname in os.listdir(lib):
                    add_path(os.path.join(lib, modname))
            else:
                for dirname in dirs:
                    if not dirname.endswith('_plugin'): continue
                    modname = os.path.join(root, dirname, '__init__.py')
                    if os.path.isfile(modname):
                        add_path(root)
                        break

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

