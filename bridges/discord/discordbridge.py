# -*- coding: utf-8 -*-
# vim: set ts=4 et

import asyncio
import discord
import json

import config


class BridgeClient(object):
    def __init__(self, bridge):
        self.bridge = bridge
        self.loop = bridge.loop

    async def start(self):
        backoff = 0
        while True:
            try:
                host, port = config.bridge[0], config.bridge[1]
                self.reader, self.writer = await asyncio.open_connection(host, port, loop=self.loop)
            except Exception:
                backoff = min(60, backoff + (backoff//2) + 1)
                print("Error connecting to gateway, backoff for %ds" % backoff)
                await asyncio.sleep(backoff, loop=self.loop)
                continue

            backoff = 0
            self.recvbuf = b''

            data = json.dumps({'type': 'auth', 'secret': config.bridge_secret, 'realm': config.realm})
            self.writer.write(data.encode() + b'\r\n')
            print("Connected to gateway")

            try:
                while True:
                    await self.process()
            except Exception as e:
                print(e)
                self.writer.close()

    async def process(self):
        data = await self.reader.read(1024)
        if not data:
            raise Exception("Gateway connection closed")

        self.recvbuf += data
        parts = self.recvbuf.split(b'\r\n')
        lines, self.recvbuf = parts[:-1], parts[-1]

        for line in lines:
            obj = json.loads(line.decode('utf-8'))
            if obj['type'] in ['message', 'action']:
                await self.bridge.discord_client.send(obj)


class DiscordClient(discord.Client):
    def __init__(self, bridge):
        discord.Client.__init__(self)
        self.bridge = bridge
        self.loop = bridge.loop
    
    async def on_ready(self):
        print("Connected to discord")

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return
        
        if message.clean_content:
            if message.clean_content.startswith('_') and message.clean_content.endswith('_'):
                obj = {'type': 'action',
                       'realm': config.realm,
                       'channel': '#' + message.channel.name,
                       'username': message.author.display_name,
                       'message': message.clean_content[1:-1]}
            else:
                obj = {'type': 'message',
                       'realm': config.realm,
                       'channel': '#' + message.channel.name,
                       'username': message.author.display_name,
                       'message': message.clean_content}
            s = json.dumps(obj).encode('utf-8') + b'\r\n'
            self.bridge.bridge_client.writer.write(s)

        for attachment in message.attachments:
            obj = {'type': 'message',
                   'realm': config.realm,
                   'channel': '#' + message.channel.name,
                   'username': message.author.display_name,
                   'message': attachment['url']}
            s = json.dumps(obj).encode('utf-8') + b'\r\n'
            self.bridge.bridge_client.writer.write(s)

    async def send(self, obj):
        for channel in self.get_all_channels():
            if '#' + channel.name == obj['channel']:
                text = obj['message']
                for word in text.split():
                    if word.startswith('@'):
                        name = word[1:]
                        for member in channel.server.members:
                            if member.display_name.lower() == name.lower():
                                text = text.replace(word, '<@%s>' % member.id)
                                break
                    if word.startswith('#'):
                        name = word[1:]
                        for chan in channel.server.channels:
                            if chan.name.lower() == name.lower():
                                text = text.replace(word, '<#%s>' % chan.id)
                                break

                if obj['type'] == 'message':
                    await self.send_message(channel, '<%s> %s' % (obj['username'], text))
                elif obj['type'] == 'action':
                    await self.send_message(channel, '* %s %s' % (obj['username'], text))

    async def start(self, token):
        backoff = 0
        while True:
            try:
                await discord.Client.start(self, token)
            except:
                self.logout()
                backoff = min(60, backoff + (backoff//2) + 1)
                print("Error connecting to discord, backoff for %ds" % backoff)
                await asyncio.sleep(backoff, loop=self.loop)
                continue
            backoff = 0


class DiscordBridge(object):    
    def run(self):
        self.loop = asyncio.get_event_loop()

        self.bridge_client = BridgeClient(self)
        self.discord_client = DiscordClient(self)
        
        futures = []
        futures.append(self.bridge_client.start())
        futures.append(self.discord_client.start(config.bot_token))

        self.loop.run_until_complete(asyncio.wait(futures))
        self.loop.close()
