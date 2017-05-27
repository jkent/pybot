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
    def config_save_trigger(self, msg, args, argstr):
        with open(self.bot.configfile, 'w') as configfile:
            self.bot.config.write(configfile)
        msg.reply('Configuration saved')
        
    @hook
    def config_set_trigger(self, msg, args, argstr):
        try:
            section, key, value = argstr.split(None, 2)
        except:
            msg.reply('usage: config set SECTION KEY VALUE')
            return

        if not self.bot.config.has_section(section):
            self.bot.config.add_section(section)
        self.bot.config.set(section, key, value)

    @hook
    def config_unset_trigger(self, msg, args, argstr):
        try:
            section, key = argstr.split(None, 2)
        except:
            msg.reply('usage: config unset SECTION KEY')
        self.bot.config.remove_option(section, key)

        if len(self.bot.config.options(section)) == 0:
            self.bot.config.remove_section(section)

    @hook
    def config_list_trigger(self, msg, args, argstr):
        if not argstr:
            msg.reply('usage: config list SECTION')
            return
        
        if not self.bot.config.has_section(argstr):
            msg.reply('no section %s' % argstr)
            return

        for option in self.bot.config.options(argstr):
            value = self.bot.config.get(argstr, option)
            msg.reply('%s = %s' % (option, value))
