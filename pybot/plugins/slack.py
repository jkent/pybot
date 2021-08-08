# -*- coding: utf-8 -*-
# vim: set ts=4 et

import os
import re
import sqlite3
from hashlib import md5

from pybot.plugin import *
from slack_sdk.rtm_v2 import RTMClient


class Plugin(BasePlugin):
    def on_load(self):
        dbfile = os.path.join(self.bot.core.data_path, self.bot.network +
                '.slack.db')
        self.db = sqlite3.connect(dbfile, check_same_thread=False)
        self.db.row_factory = sqlite3.Row

        self.db.execute('''
        CREATE TABLE IF NOT EXISTS bridges (
            id INTEGER PRIMARY KEY NOT NULL,
            irc_channel TEXT NOT NULL,
            slack_channel TEXT NOT NULL,
            UNIQUE(irc_channel, slack_channel)
        );''')

        self.db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY NOT NULL,
            irc_name TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            slack_name TEXT,
            UNIQUE(irc_name, email, slack_name)
        );''')

        self.db.commit()

        self.rtm = RTMClient(token=self.config['bot_token'])
        self.rtm.connect()

        self.slack_channels = []
        result = self.rtm.web_client.conversations_list(
            limit=100,
            exclude_archived=True
        )
        while result['ok']:
            for channel in result['channels']:
                self.slack_channels.append(channel)
            next_cursor = result.get('response_metadata', {}).get('next_cursor')
            if not next_cursor:
                break
            result = self.rtm.web_client.conversations_list(
                limit=100,
                cursor=next_cursor
            )

        self.slack_users = []
        result = self.rtm.web_client.users_list(
            limit=100
        )
        while result['ok']:
            for user in result['members']:
                self.slack_users.append(user)
            next_cursor = result.get('response_metadata', {}).get('next_cursor')
            if not next_cursor:
                break
            result = self.rtm.web_client.users_list(
                limit=100,
                cursor=next_cursor
            )


        @self.rtm.on('message')
        def slack_message(client: RTMClient, event: dict):

            slack_name = self.irc_name_from_slack_id(event['user'])
            text = event['text']

            m = re.search(r'<@[UW][0-9A-Z]{8}> has joined the channel', text)
            if m:
                return

            while True:
                m = re.search(r'<@([UW][0-9A-Z]{8})>', text)
                if not m: break
                text = text.replace(m.group(0), '@%s' %
                        (self.irc_name_from_slack_id(m.group(1)),))

            for channel in self.slack_channels:
                if channel['id'] == event['channel']:
                    slack_channel = '#' + channel['name']

                    bridges = self.db.execute('''
                        SELECT irc_channel
                        FROM bridges
                        WHERE LOWER(slack_channel) = ?''',
                        (slack_channel.lower(),)
                    )

                    for bridge in bridges:
                        self.bot.privmsg(bridge['irc_channel'], '<%s> %s' % \
                                (slack_name, text))


        @self.rtm.on('channel_created')
        def slack_channel_created(client: RTMClient, event: dict):
            self.slack_channels.append(event['channel'])
            print('created', event['channel']['id'])


        @self.rtm.on('channel_archive')
        def slack_channel_archive(client: RTMClient, event: dict):
            self.slack_channels = [channel for channel in self.slack_channels \
                    if channel['id'] != event['channel']]
            print('archive', event['channel'])


        @self.rtm.on('channel_unarchive')
        def slack_channel_unarchive(client: RTMClient, event: dict):
            result = self.rtm.web_client.conversations_info(
                channel = event['channel']
            )
            if result['ok']:
                self.slack_channels.append(event['channel'])
                print('unarchived', event['channel'])


        @self.rtm.on('channel_deleted')
        def slack_channel_deleted(client: RTMClient, event: dict):
            self.slack_channels = [channel for channel in self.slack_channels \
                    if channel['id'] != event['channel']]
            print('deleted', event['channel'])


        @self.rtm.on('channel_rename')
        def slack_channel_rename(client: RTMClient, event: dict):
            for channel in self.slack_channels:
                if channel['id'] == event['channel']['id']:
                    channel['name'] = event['channel']['name']


        @self.rtm.on('user_change')
        def slack_user_change(client: RTMClient, event: dict):
            for i, user in enumerate(self.slack_users):
                if user['id'] == event['user']['id']:
                    self.slack_users[i] = event['user']
                    return

            self.slack_users.append(event['user'])


        @self.rtm.on('member_joined_channel')
        def slack_member_joined_channel(client: RTMClient, event: dict):
            event['user'] = self.slack_get_user(event['user'])

            found = False
            for i, user in enumerate(self.slack_users):
                if user['id'] == event['user']['id']:
                    self.slack_users[i] = event['user']
                    found = True
                    break

            if not found:
                self.slack_users.append(event['user'])

            for channel in self.slack_channels:
                if channel['id'] == event['channel']:
                    break

            slack_channel = '#' + channel['name']
            bridges = self.db.execute('''
                SELECT irc_channel
                FROM bridges
                WHERE LOWER(slack_channel) = ?''', (slack_channel.lower(),)
            )
            for bridge in bridges:
                text = '%s joined slack channel %s' % \
                        (self.irc_name_from_slack_id(event['user']['id']),
                        slack_channel)
                self.bot.privmsg(bridge['irc_channel'], text)


        @self.rtm.on('member_left_channel')
        def slack_member_left_channel(client: RTMClient, event: dict):
            for channel in self.slack_channels:
                if channel['id'] == event['channel']:
                    break

            slack_channel = '#' + channel['name']
            bridges = self.db.execute('''
                SELECT irc_channel
                FROM bridges
                WHERE LOWER(slack_channel) = ?''', (slack_channel.lower(),)
            )
            for bridge in bridges:
                text = '%s left slack channel %s' % \
                        (self.irc_name_from_slack_id(event['user']),
                        slack_channel)
                self.bot.privmsg(bridge['irc_channel'], text)


    def on_unload(self):
        self.db.close()
        self.rtm.disconnect()
        self.rtm.close()


    def irc_name_from_slack_id(self, id):
        email = ''
        name = None
        for user in self.slack_users:
            if user['id'] == id:
                email = user['profile']['email']
                slack_name = user['real_name']
                break

        user = self.db.execute('''
            SELECT irc_name
            FROM users
            WHERE LOWER(email) = ?''', (email.lower(),)
        ).fetchone()

        name = user['irc_name'] if user else slack_name
        return name


    def slack_get_user(self, id):
        response = self.rtm.web_client.users_info(
            user=id,
        )
        if response['ok']:
            return response['user']


    def slack_get_channel(self, id):
        response = self.rtm.web_client.conversations_info(
            channel=id,
        )
        if response['ok']:
            return response['channel']


    @level(900)
    @hook
    def slack_bridge_list_trigger(self, msg, args, argstr):
        bridges = self.db.execute('''
            SELECT irc_channel, slack_channel
            FROM bridges'''
        )

        for bridge in bridges:
            msg.reply('irc:%s slack:%s' % (bridge['irc_channel'],
                    bridge['slack_channel']))


    @level(900)
    @hook
    def slack_bridge_add_trigger(self, msg, args, argstr):
        if len(args) != 3:
            msg.reply('Two arguments, irc_channel and slack_channel, are ' \
                    'required')
            return

        irc_channel, slack_channel = args[1:]

        try:
            self.db.execute('''
                INSERT INTO bridges (irc_channel, slack_channel)
                VALUES (?, ?)''', (irc_channel, slack_channel)
            )
            self.db.commit()
        except:
            msg.reply('Error adding bridge, already exists?')


    @level(900)
    @hook
    def slack_bridge_del_trigger(self, msg, args, argstr):
        if len(args) != 3:
            msg.reply('Two arguments, irc_channel and slack_channel, are ' \
                    'required')
            return

        irc_channel, slack_channel = args[1:]

        try:
            self.db.execute('''
                DELETE FROM bridges
                WHERE irc_channel = ? AND slack_channel = ?
                ''', (irc_channel, slack_channel)
            )
            self.db.commit()
        except:
            msg.reply('Error deleting bridge, not exist?')


    @hook
    def slack_register_trigger(self, msg, args, argstr):
        if len(args) < 2:
            msg.reply('Email required, with an optional slack name')
            return

        email, slack_name = args[1], ' '.join(args[2:])

        try:
            self.db.execute('''
                INSERT OR REPLACE INTO users (irc_name, email, slack_name)
                VALUES (?, ?, ?)''', (msg.source, email,
                slack_name if slack_name else None)
            )
            self.db.commit()
            msg.reply('Thanks, you\'re registered!')
        except:
            msg.reply('Registration error')


    @hook
    def privmsg_command(self, msg):
        if msg.trigger or not msg.channel:
            return

        markdown = False
        text = msg.param[-1]
        if text.startswith('\x01ACTION'):
            text = '_' + text[8:-1] + '_'
            markdown = True

        user = self.db.execute('''
            SELECT email, slack_name
            FROM users
            WHERE LOWER(irc_name) = ?''', (msg.source.lower(),)
        ).fetchone()
        name = user['slack_name'] if user and user['slack_name'] else msg.source
        icon = 'https://www.gravatar.com/avatar/%s?s=48&d=identicon' % \
                (md5(user['email'].lower().encode('utf-8')).hexdigest(),) if \
                        user and user['email'] else None

        bridges = self.db.execute('''
            SELECT slack_channel
            FROM bridges
            WHERE LOWER(irc_channel) = ?''', (msg.channel.lower(),)
        )
        for bridge in bridges:
            self.rtm.web_client.chat_postMessage(
                channel=bridge['slack_channel'],
                text=text,
                as_user=False,
                username=name,
                icon_url=icon,
                mrkdwn=markdown
            )


    @hook
    def join_command(self, msg):
        user = self.db.execute('''
            SELECT email, slack_name
            FROM users
            WHERE LOWER(irc_name) = ?''', (msg.source.lower(),)
        ).fetchone()
        name = user['slack_name'] if user and user['slack_name'] else msg.source
        icon = 'https://www.gravatar.com/avatar/%s?s=48&d=identicon' % \
                (md5(user['email'].lower().encode('utf-8')).hexdigest(),) if \
                        user and user['email'] else None

        found = False
        if user:
            for slack_user in self.slack_users:
                if slack_user['profile'].get('email') == user['email'] or \
                        slack_user['name'] == user['slack_name']:
                    found = True
                    break

        if found:
            text = '<@%s> left the IRC channel %s' % (slack_user['id'],
                    msg.param[0])
        else:
            text = '%s left the IRC channel %s' % (msg.source, msg.param[0])

        bridges = self.db.execute('''
            SELECT slack_channel
            FROM bridges
            WHERE LOWER(irc_channel) = ?''', (msg.param[0].lower(),)
        )
        for bridge in bridges:
            self.rtm.web_client.chat_postMessage(
                channel=bridge['slack_channel'],
                text=text,
                as_user=False,
                username=name,
                icon_url=icon,
            )


    @hook
    def part_command(self, msg):
        user = self.db.execute('''
            SELECT email, slack_name
            FROM users
            WHERE LOWER(irc_name) = ?''', (msg.source.lower(),)
        ).fetchone()
        name = user['slack_name'] if user and user['slack_name'] else msg.source
        icon = 'https://www.gravatar.com/avatar/%s?s=48&d=identicon' % \
                (md5(user['email'].lower().encode('utf-8')).hexdigest(),) if \
                        user and user['email'] else None

        found = False
        for slack_user in self.slack_users:
            if slack_user['profile'].get('email') == user['email'] or \
                    slack_user['name'] == user['slack_name']:
                found = True
                break

        if found:
            text = '<@%s> joined the IRC channel %s' % (slack_user['id'],
                    msg.param[0])
        else:
            text = '%s joined the IRC channel %s' % (msg.source, msg.param[0])

        bridges = self.db.execute('''
            SELECT slack_channel
            FROM bridges
            WHERE LOWER(irc_channel) = ?''', (msg.param[0].lower(),)
        )
        for bridge in bridges:
            self.rtm.web_client.chat_postMessage(
                channel=bridge['slack_channel'],
                text=text,
                as_user=False,
                username=name,
                icon_url=icon,
            )
