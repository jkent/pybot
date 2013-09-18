# -*- coding: utf-8 -*-
# vim: set ts=4 et


class SelectableInterface(object):
    def fileno(self):
        return None

    def on_tick(self, time_now):
        return

    def can_read(self):
        return False

    def can_write(self):
        return False

    def do_read(self):
        return

    def do_write(self):
        return

