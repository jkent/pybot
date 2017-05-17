# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    @hook
    def reload_config_trigger(self, msg, args, argstr):
        self.bot.config.read(self.bot.configfile)
        msg.reply('Configuration reloaded')

    @hook
    def save_config_trigger(self, msg, args, argstr):
        with open(self.bot.configfile, 'w') as configfile:
            self.bot.config.write(configfile)
        msg.reply('Configuration saved')
        
    @hook
    @level(1000)
    def set_config_trigger(self, msg, args, argstr):
        try:
            section, key, value = argstr.split(None, 3)
        except:
            value = None
            try:
                section, key = argstr.split(None, 2)
            except:
                msg.reply('usage: set config SECTION KEY [VALUE]')
                return

        if value == None:
            try:
                del self.bot.config[section][key]
            except:
                msg.reply('Key does not exist')
        else:
            if section not in self.bot.config:
                self.bot.config[section] = {}
            self.bot.config[section][key] = value

    @hook
    @level(1000)
    def list_config_trigger(self, msg, args, argstr):
        section = argstr
        for key in self.bot.config[section]:
            value = self.bot.config[section][key]
            msg.reply('%s = %s' % (key, value))
