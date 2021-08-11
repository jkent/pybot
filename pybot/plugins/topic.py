# -*- coding: utf-8 -*-
# vim: set ts=4 et

from datetime import datetime, timedelta
from pybot.plugin import *


class Plugin(BasePlugin):
    def on_load(self):
        self.last = {}


    @hook
    def topic_set_trigger(self, msg, args, argstr):
        now = datetime.utcnow()

        level = msg.permissions.get('topic', msg.permissions.get('ANY'))

        if msg.channel == None:
            msg.reply("Can't change a channel topic from within a DM")
            return
        elif level < self.config.get('min_level', 100):
            last = self.last.get(msg.channel, {})
            last['proposed'] = argstr
            self.last[msg.channel] = last
            msg.reply("Permission denied")
            return
        elif msg.channel not in self.last or not self.last[msg.channel].get('time'):
            pass
        elif level >= self.config.get('bypass_level', 900):
            pass
        else:
            last = self.last[msg.channel]
            last['proposed'] = argstr
            min_age = self.config.get('min_age', '24h')

            n, unit = int(min_age[:-1]), min_age[-1]
            if unit == 'm':
                delta = timedelta(minutes=n)
            elif unit == 'h':
                delta = timedelta(hours=n)
            elif unit == 'd':
                delta = timedelta(days=n)
            elif unit == 'w':
                delta = timedelta(weeks=n)

            if not now >= last['time'] + delta:
                delta -= now - last['time']
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                seconds = delta.seconds % 60

                msg.reply("You must wait %d day(s), %d hour(s), %d minute(s) "
                        "and %d second(s) to change the topic" % (delta.days,
                        hours, minutes, seconds))
                return

        self.bot.send("TOPIC %s :%s" % (msg.channel, argstr))
        self.last[msg.channel] = {'time': now, 'proposed': None}


    @hook
    def topic_apply_trigger(self, msg, args, argstr):
        level = msg.permissions.get('topic', msg.permissions.get('ANY'))

        if level < self.config.get('bypass_level', 900):
            msg.reply("Permission denied")
            return

        last = self.last.get(msg.channel)
        if not last or not last['proposed']:
            msg.reply("No proposed topic to apply")
            return

        self.bot.send("TOPIC %s :%s" % (msg.channel, last['proposed']))
        self.last[msg.channel] = {'time': datetime.utcnow(), 'proposed': None}
