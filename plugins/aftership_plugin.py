# -*- coding: utf-8 -*-
# vim: set ts=4 et

from datetime import datetime
import os
import re
import requests
import sqlite3

from plugin import *

API_ENDPOINT = 'https://api.aftership.com/v4'

class Plugin(BasePlugin):
    def on_load(self, reload):
        self.db = sqlite3.connect(os.path.join(self.bot.core.data_path,
            'aftership.db'), detect_types=sqlite3.PARSE_DECLTYPES)
        self.db.row_factory = sqlite3.Row
        self.cur = self.db.cursor()
        self.cur.execute('''CREATE TABLE IF NOT EXISTS trackings
            (id TEXT PRIMARY KEY, checkpoint_count INTEGER)''')
        self.db.commit()

        if self.bot.nick:
            self.interval = self.bot.set_interval(self.on_tick, 5*60, self)
            self.on_tick()
        else:
            self.interval = self.bot.set_interval(self.on_check, 1, self)

    def on_unload(self, reload):
        self.bot.hooks.uninstall(self.interval)
        self.db.close()

    def on_check(self):
        if not self.bot.nick:
            return

        self.bot.hooks.uninstall(self.interval)
        self.interval = self.bot.set_interval(self.on_tick, 5*60, self)
        self.on_tick()

    def on_tick(self):
        url = API_ENDPOINT + '/trackings'
        headers = {'aftership-api-key': self.config_get('api_key'),
            'Content-Type': 'application/json'}
        r = requests.get(url, headers=headers)
        json = r.json()
        trackings = json['data']['trackings']
        for tracking in trackings:
            irc_nickname = None
            if 'custom_fields' in tracking:
                custom_fields = tracking['custom_fields']
                if custom_fields and 'irc_nickname' in custom_fields:
                    irc_nickname = tracking['custom_fields']['irc_nickname']

            if irc_nickname == None:
                continue

            tracking_id = tracking['id']
            checkpoint_count = len(tracking['checkpoints'])
            self.cur.execute('''SELECT checkpoint_count FROM trackings
                WHERE id = ? LIMIT 1''', (tracking_id,))
            try:
                row = self.cur.fetchone()
                old_checkpoint_count = row['checkpoint_count']
                if checkpoint_count <= old_checkpoint_count:
                    continue
            except:
                old_checkpoint_count = 0

            self.cur.execute('''INSERT OR REPLACE INTO trackings
                (id, checkpoint_count) VALUES (?, ?)''', (tracking_id,
                checkpoint_count))

            title = tracking['title']
            tracking_number = tracking['tracking_number']
            title = None if tracking_number == title else title

            if title:
                message = 'aftership: Update on your %s (%s: %s)' % (title,
                    tracking['slug'], tracking_number)
            else:
                message = 'aftership: Update on %s: %s' % (tracking['slug'], 
                    tracking_number)
                
            self.bot.privmsg(irc_nickname, message)

            checkpoints = tracking['checkpoints']
            for checkpoint in checkpoints[old_checkpoint_count:]:
                checkpoint_time = \
                    datetime.strptime(
                        checkpoint['checkpoint_time'], "%Y-%m-%dT%H:%M:%S")

                location = ''
                if checkpoint['state']:
                    if checkpoint['city']:
                        location += checkpoint['city'] + ', '
                    location += checkpoint['state']
                elif checkpoint['country_name']:
                    if checkpoint['city']:
                        location += checkpoint['city'] + ', '
                    location += checkpoint['country_name']
                elif checkpoint['city']:
                    location += checkpoint['city']

                message = "%s %s" % \
                    (checkpoint_time.strftime("%Y-%m-%d %H:%M"),
                        checkpoint['message'])
                if location:
                    message += ' (%s)' % location
                self.bot.privmsg(irc_nickname, message)

        self.db.commit()

    @hook
    def aftership_add_trigger(self, msg, args, argstr):
        m = re.match(r"(?:\[(.*)\]\s+)?(\w+)(?:\s+(.+))?", argstr)
        if not m:
            msg.reply("invalid tracking spec")
            return

        slug, tracking_number, title = m.groups()
    
        tracking = {'tracking_number': tracking_number,
            'custom_fields': {'irc_nickname': msg.source}}
        if slug:
            tracking['slug'] = slug
        if title:
            tracking['title'] = title

        url = API_ENDPOINT + '/trackings'
        request_data = {'tracking': tracking}
        headers = {'aftership-api-key': self.config_get('api_key'),
            'Content-Type': 'application/json'}
        r = requests.post(url, headers=headers, json=request_data)

        json = r.json()
        if json['meta']['code'] != 201:
            msg.reply('invalid tracking')

        tracking_id = json['data']['tracking']['id']
        self.cur.execute('''INSERT INTO trackings (id, checkpoint_count)
            VALUES (?, 0)''', (tracking_id,))
        self.db.commit()

        msg.reply('tracking added')
