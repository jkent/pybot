# -*- coding: utf-8 -*-
# vim: set ts=4 et

from hashlib import md5
import re

from pybot.plugin import *
from slack_sdk.rtm_v2 import RTMClient
from sqlalchemy import func

from . import models
from .models import *


class Plugin(BasePlugin):
    def on_load(self):
        self.db = models.init(self.bot)

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

            for i, user in enumerate(self.slack_users):
                if user['id'] == event['user']['id']:
                    self.slack_users[i] = event['user']
                    return

            self.slack_users.append(event['user'])


        @self.rtm.on('message')
        def slack_message(client: RTMClient, event: dict):
            slack_name = self.slack_name_from_id(event['user'])
            text = event['text']

            while True:
                m = re.search(r'<@([UW][0-9A-Z]{8})>', text)
                if not m: break
                text = text.replace(m.group(0), '@%s' %
                        (self.slack_name_from_id(m.group(1)),))

            for channel in self.slack_channels:
                if channel['id'] == event['channel']:
                    slack_channel = '#' + channel['name']
                    bridges = self.db.query(Bridge) \
                            .filter(func.lower(Bridge.slack_channel)== \
                                    func.lower(slack_channel))
                    for bridge in bridges:
                        self.bot.privmsg(bridge.irc_channel, '<%s> %s' % \
                                (slack_name, text))


    def on_unload(self):
        self.db.close()
        self.rtm.disconnect()


    def slack_name_from_id(self, id):
        name = 'UNKNOWN'
        for user in self.slack_users:
            if user['id'] == id:
                email = user['profile']['email']
                slack_name = user['real_name']
                break

        user = self.db.query(User) \
                .filter(func.lower(User.email)==func.lower(email)).first()
        name = user.irc_name if user else slack_name
        return name


    def slack_get_user(self, id):
        response = self.rtm.web_client.users_info(
            user=id,
        )
        if response['ok']:
            return response['user']


    @level(900)
    @hook
    def slack_bridge_list_trigger(self, msg, args, argstr):
        bridges = self.db.query(Bridge)
        for bridge in bridges:
            msg.reply('irc:%s slack:%s' % (bridge.irc_channel,
                    bridge.slack_channel))


    @level(900)
    @hook
    def slack_bridge_add_trigger(self, msg, args, argstr):
        if len(args) != 3:
            msg.reply('Two arguments, irc_channel and slack_channel, are ' \
                    'required')
            return

        irc_channel, slack_channel = args[1:]
        bridge = Bridge(irc_channel, slack_channel)
        self.db.add(bridge)
        self.db.commit()


    @level(900)
    @hook
    def slack_bridge_del_trigger(self, msg, args, argstr):
        if len(args) != 3:
            msg.reply('Two arguments, irc_channel and slack_channel, are ' \
                    'required')
            return

        irc_channel, slack_channel = args[1:]
        bridge = self.db.query(Bridge).filter(Bridge.irc_channel==irc_channel) \
                .filter(Bridge.slack_channel==slack_channel).first()
        self.db.delete(bridge)
        self.db.commit()


    @hook
    def slack_register_trigger(self, msg, args, argstr):
        if len(args) < 2:
            msg.reply('Email required, with an optional slack name')
            return

        email, slack_name = args[1], ' '.join(args[2:])

        print(slack_name)

        user = User(msg.source, email, slack_name if slack_name else None)
        self.db.add(user)
        self.db.commit()

        msg.reply('Thanks, you\'re registered!')


    @hook
    def privmsg_command(self, msg):
        if msg.trigger or not msg.channel:
            return

        user = self.db.query(User) \
                .filter(func.lower(User.irc_name)==func.lower(msg.source)) \
                .first()
        name = user.slack_name if user and user.slack_name else msg.source
        icon = 'https://www.gravatar.com/avatar/%s?s=48' % \
                (md5(user.email.lower().encode('utf-8')).hexdigest() if \
                        user and user.email else None,)

        bridges = self.db.query(Bridge) \
                .filter(func.lower(Bridge.irc_channel)==msg.channel)
        for bridge in bridges:
            self.rtm.web_client.chat_postMessage(
                channel=bridge.slack_channel,
                text=msg.param[-1],
                as_user=False,
                username=name,
                icon_url=icon
            )
