# -*- coding: utf-8 -*-
# vim: set ts=4 et

import json
import os
import sqlite3

import pybot.config as config
from pybot.plugin import *


class Plugin(BasePlugin):
    default_level = 1000

    def on_load(self, reload):
        self.db = sqlite3.connect(os.path.join(self.bot.core.data_path,
                'perms.db'))
        self.cur = self.db.cursor()
        self.cur.execute('''CREATE TABLE IF NOT EXISTS allow
                     (mask TEXT PRIMARY KEY, rules TEXT)''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS deny
                     (mask TEXT PRIMARY KEY, rules TEXT)''')
        self.db.commit()
        self.load_rules()

    def on_unload(self, reload):
        self.save_rules()
        self.db.close()

    def load_rules(self):
        self.bot.allow_rules = {}
        self.bot.deny_rules = {}

        self.cur.execute('SELECT COUNT(*) FROM allow')
        count = self.cur.fetchone()[0]
        if count == 0:
            self.bot.allow_rules['*'] = {'ANY': 1}
        else:
            for mask, rules in self.cur.execute('SELECT mask, rules ' \
                    'FROM allow'):
                self.bot.allow_rules[mask] = json.loads(rules)

            for mask, rules in self.cur.execute('SELECT mask, rules FROM ' \
                    'deny'):
                self.bot.deny_rules[mask] = json.loads(rules)

        superuser = config.config[self.bot.network].get('plugins', {}) \
                .get('perms', {}).get('superuser')
        if superuser:
            self.bot.allow_rules[superuser] = {'ANY': 1000}

    def save_rules(self):
        for mask, rules in list(self.bot.allow_rules.items()):
            rules = json.dumps(rules)
            self.cur.execute('INSERT OR REPLACE INTO allow (mask, rules) ' \
                    'VALUES (?, ?)', (mask, rules))

        for mask, rules in list(self.bot.deny_rules.items()):
            rules = json.dumps(rules)
            self.cur.execute('INSERT OR REPLACE INTO deny (mask, rules) ' \
                    'VALUES (?, ?)', (mask, rules))

        self.db.commit()

    @hook
    def perms_list_trigger(self, msg, args, argstr):
        msg.reply('Allow:')
        for mask, rules in list(self.bot.allow_rules.items()):
            line = '  ' + mask
            for plugin, level in list(rules.items()):
                line += ' %s=%s' % (plugin, level)
            msg.reply(line)

        msg.reply('Deny:')
        for mask, rules in list(self.bot.deny_rules.items()):
            line = '  ' + mask
            for plugin, level in list(rules.items()):
                line += ' %s=%s' % (plugin, level)
            msg.reply(line)

    @hook
    def perms_allow_trigger(self, msg, args, argstr):
        if len(args) < 2:
            msg.reply('a prefix mask is required')
            return

        mask = args[1]
        if mask.startswith('-'):
            if len(args) != 2:
                msg.reply('only one argument expected')
            mask = mask[1:]
            if mask in self.bot.allow_rules:
                del self.bot.allow_rules[mask]
                self.cur.execute('DELETE FROM allow WHERE mask=?', (mask,))
                self.db.commit()
            return

        rules = self.bot.allow_rules.setdefault(mask, {})

        for arg in args[2:]:
            if arg.startswith('-'):
                plugin = arg[1:]
                try:
                    del rules[plugin]
                except:
                    msg.reply('no rule exists for plugin "%s"' % plugin)
                    return
            else:
                try:
                    plugin, level = arg.split('=', 1)
                    level = int(level)
                except:
                    msg.reply('invalid syntax, "plugin=level" format required')
                    return
                rules[plugin] = level

    @hook
    def perms_deny_trigger(self, msg, args, argstr):
        if len(args) < 2:
            msg.reply('a prefix mask is required')
            return

        mask = args[1]
        if mask.startswith('-'):
            if len(args) != 2:
                msg.reply('only one argument expected')
            mask = mask[1:]
            if mask in self.bot.deny_rules:
                del self.bot.deny_rules[mask]
                self.cur.execute('DELETE FROM deny WHERE mask=?', (mask,))
                self.db.commit()
            return

        rules = self.bot.deny_rules.setdefault(mask, {})

        for arg in args[2:]:
            if arg.startswith('-'):
                plugin = arg[1:]
                try:
                    del rules[plugin]
                except:
                    msg.reply('no rule exists for plugin "%s"' % plugin)
                    return
            else:
                try:
                    plugin, level = arg.split('=', 1)
                    level = int(level)
                except:
                    msg.reply('invalid syntax, "plugin=level" format required')
                    return
                rules[plugin] = level
