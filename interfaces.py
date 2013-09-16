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


class PluginInterface(object):
    def on_load(self):
        pass

    def on_unload(self):
        pass

    def on_tick(self, time_now):
        pass

    def on_message(self, parts):
        pass

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

