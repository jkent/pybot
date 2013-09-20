# -*- coding: utf-8 -*-
# vim: set ts=4 et

class SelectableInterface(object):
    connected = False

    def fileno(self):
        return None

    def can_read(self):
        return False

    def can_write(self):
        return False

    def do_read(self):
        return

    def do_write(self):
        return

    def do_tick(self, time_now):
        return

