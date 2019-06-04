# -*- coding: utf-8 -*-
# vim: set ts=4 et

from datetime import datetime, timedelta
import re
from sqlalchemy import or_, and_

from plugin import *
from . import models
from .models import *


RETRY_INTERVAL = 3600


class Plugin(BasePlugin):
    def on_load(self, reload):
        self.db = models.init(self.bot)

    def on_unload(self, reload):
        self.db.close()

    @hook
    def message_send_trigger(self, msg, args, argstr):
        try:
            addressee, text = argstr.strip().split(None, 1)
        except:
            msg.reply('Expected: <addressee> <text>')
            return True

        optout = self.db.query(Preference).filter_by(nick=addressee, key='optout').first()
        if optout and optout.value.lower() == 'true':
            msg.reply('Recipient has opted out of messages.')
            return True

        channel = msg.channel
        delta = None

        while True:
            m = re.match(r'.*\s+(as dm|in \d{1,3}[mhdw])$', text)
            if not m:
                break

            cmd = m.group(1)
            if cmd == 'as dm':
                channel = None
            elif cmd.startswith('in '):
                n, unit = int(cmd[3:-1]), cmd[-1]
                if unit == 'm':
                    delta = timedelta(minutes=n)
                elif unit == 'h':
                    delta = timedelta(hours=n)
                elif unit == 'd':
                    delta = timedelta(days=n)
                elif unit == 'w':
                    delta = timedelta(weeks=n)

            text = re.sub(cmd, '', text)

        if not self.db.query(Block).filter_by(nick=addressee, block=msg.source).first():
            message = Message(msg.source, addressee, text, channel, delta)
            self.db.add(message)
            self.db.commit()

        msg.reply('Message queued!')
        return True

    @hook
    @hook('ack')
    def message_ack_trigger(self, msg, args, argstr):
        if len(args) != 1:
            msg.reply('No arguments allowed.')
            return True

        count = 0
        query = self.db.query(Message).filter_by(addressee=msg.source)
        for message in query:
            count += 1
            self.db.delete(message)
    
        if count:
            self.db.commit()
            msg.reply('Ack\'d %d message%s.' % (count, 's' if count > 1 else ''))
        else:
            msg.reply('No messages to ack.')
        
        return True


    @hook
    def message_list_trigger(self, msg, args, argstr):
        if len(args) != 1:
            msg.reply('No arguments allowed.')
            return True

        query = self.db.query(Message).filter_by(nick=msg.source)
        for message in query:
            text = '(%d) %s: %s' % (message.id, message.addressee, message.text)
            msg.reply(text, direct=True)

        query = self.db.query(Message).filter_by(addressee=msg.source, presented=True)
        for message in query:
            text = '(%d) <%s> %s' % (message.id, message.nick, message.text)
            msg.reply(text, direct=True)

        return True


    @hook
    def message_del_trigger(self, msg, args, argstr):
        if len(args) != 2:
            msg.reply('Expected: <id>')
            return True

        try:
            id = int(args[1])
        except:
            msg.reply('Expected: <id>')
            return True

        message = self.db.query(Message).filter_by(id=id) \
            .filter(or_(Message.nick == msg.source, and_(Message.addressee == msg.source, Message.presented == True))).first()
        if message:
            self.db.delete(message)
            msg.reply('Message deleted.')
        else:
            msg.reply('Unknown message.')

        return True


    @hook
    def message_opt_trigger(self, msg, args, argstr):
        if len(args) != 2 or args[1].lower() not in ['in', 'out']:
            msg.reply('Expected: <in | out>')
            return True

        optout = self.db.query(Preference).filter_by(nick=msg.source, key='optout').first()
        if not optout:
            optout = Preference(msg.source, 'optout', 'False')
        
        optout.value = 'False'
        if args[1].lower() == 'out':
            optout.value = 'True'

        self.db.add(optout)        
        self.db.commit()
        return True


    @hook
    def message_block_trigger(self, msg, args, argstr):
        if len(args) != 2:
            msg.reply('Expected: <nick>')
            return True

        try:
            block = Block(msg.source, args[1])
            self.db.add(block)
            msg.reply('Blocked %s.' % (args[1],))
        except:
            msg.reply('Already blocked.')
        
        return True


    @hook
    def message_unblock_trigger(self, msg, args, argstr):
        if len(args) != 2:
            msg.reply('Expected: <nick>')
            return True

        block = self.db.query(Block).filter_by(nick=msg.source, block=args[1]).first()
        if block:
            self.db.delete(block)
            msg.reply('Unblocked %s.' % (args[1],))
        else:
            msg.reply('Not blocked.')
        
        return True


    @hook
    def privmsg_command(self, msg):
        now = datetime.utcnow()

        query = self.db.query(Message).filter_by(addressee=msg.source) \
            .filter(Message.next_notify < now)

        presented = False

        for message in query:
            if message.channel and message.channel != msg.channel:
                continue

            text = '<%s> %s' % (message.nick, message.text)

            if message.channel:
                msg.reply('%s: %s' % (message.addressee, text))
            else:
                msg.reply(text, True)

            message.presented = True
            message.next_notify = now + timedelta(seconds=RETRY_INTERVAL)
            self.db.add(message)
        
        if presented:
            self.db.commit()
