# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *


class Plugin(BasePlugin):
    default_level = 1000
    
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
    def set_config_trigger(self, msg, args, argstr):
        try:
            section, key, value = argstr.split(None, 2)
        except:
            msg.reply('usage: set config SECTION KEY VALUE')
            return

        if not self.bot.config.has_section(section):
            self.bot.config.add_section(section)
        self.bot.config.set(section, key, value)

    @hook
    def unset_config_trigger(self, msg, args, argstr):
        try:
            section, key = argstr.split(None, 2)
        except:
            msg.reply('usage: unset config SECTION KEY')
        self.bot.config.remove_option(section, key)

    @hook
    def list_config_trigger(self, msg, args, argstr):
        section = argstr
        for option in self.bot.config.options(section):
            value = self.bot.config.get(section, option)
            msg.reply('%s = %s' % (option, value))
