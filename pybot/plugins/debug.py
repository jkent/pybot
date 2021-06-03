# -*- coding: utf-8 -*-
# vim: set ts=4 et

from pybot.plugin import *


class Plugin(BasePlugin):
    default_level = 900


    @hook
    def raw_trigger(self, msg, args, argstr):
        self.bot.send(argstr)


    @hook
    def recv_event(self, line):
        print('>> %s' % line)


    @hook
    def send_event(self, line):
        print('<< %s' % line)


    @hook
    def plugin_loading_event(self, name):
        print('loading plugin %s' % name)


    @hook
    def plugin_loaded_event(self, name):
        print('loaded plugin %s' % name)


    @hook
    def plugin_reloading_event(self, name):
        print('reloading plugin %s' % name)


    @hook
    def plugin_reloaded_event(self, name):
        print('reloaded plugin %s' % name)


    @hook
    def plugin_unloading_event(self, name):
        print('unloading plugin %s' % name)


    @hook
    def plugin_unloaded_event(self, name):
        print('unloaded plugin %s' % name)


    @level(1000)
    @hook
    def eval_trigger(self, msg, args, argstr):
        try:
            result = eval(argstr, globals(), locals())
        except Exception as e:
            result = e
        msg.reply(repr(result))
