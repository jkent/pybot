# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *

class Plugin(BasePlugin):
    @hook
    def recv_event(self, line):
        print('>> ' + line)

    @hook
    def send_event(self, line):
        print('<< ' + line)
        
    @hook
    def plugin_loading_event(self, name):
        print('loading plugin', name)
        
    @hook
    def plugin_loaded_event(self, name):
        print('loaded plugin', name)
    
    @hook
    def plugin_reloading_event(self, name):
        print('reloading plugin', name)
    
    @hook
    def plugin_reloaded_event(self, name):
        print('reloaded plugin', name)
        
    @hook
    def plugin_unloading_event(self, name):
        print('unloading plugin', name)
    
    @hook
    def plugin_unloaded_event(self, name):
        print('unloaded plugin', name)
