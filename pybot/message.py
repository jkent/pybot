# -*- coding: utf-8 -*-
# vim: set ts=4 et

import re
from datetime import datetime

from . import config


message_re = re.compile(
  '^(?:'                            +
    ':(?P<prefix>'                  +
      '(?P<source>[^ !@]+)'         +
      '(?:'                         +
        '(?:!(?P<user>[^ @]+))?'    +
        '@(?P<host>[^ ]+)'          +
      ')?'                          +
    ') '                            +
  ')?'                              +
  '(?P<cmd>[^ :]+)'                 +
  '(?: (?P<params>.+))?$'
)


def parse_params(params):
    l = []
    while params:
        if params[0] == ':':
            l.append(params[1:])
            break
        if len(l) == 14:
            l.append(params)
            break
        param, _, params = params.partition(' ')
        l.append(param)
    return l

def parse_message(message):
    match = message_re.match(message)
    if match:
        d = match.groupdict()
        d['cmd'] = d['cmd'].upper()
        d['param'] = parse_params(d['params'])
        del d['params']
    else:
        d = {'prefix': None, 'source': None, 'user': None, 'host': None,
             'command': '', 'param': []}
    return d

class Message(object):
    def __init__(self, line, bot=None):
        self.bot = bot
        self.raw = line
        self.reply_to = None
        self.time = datetime.utcnow()
        self.channel = None
        self.trigger = None
        self.level = 0
        self.__dict__.update(parse_message(line))

        if self.cmd in ('PRIVMSG', 'NOTICE'):
            if self.param[0].startswith(('&', '#', '+', '!')):
                self.channel = self.param[0].lower()
                self.reply_to = self.param[0]
            else:
                self.reply_to = self.source

        if self.cmd == 'PRIVMSG':
            self._detect_trigger()

    def _detect_trigger(self):
        text = self.param[-1]

        directed_triggers = config.config[self.bot.network] \
                .get('directed_triggers', False)
        if directed_triggers:
            if self.channel:
                if text.lower().startswith(self.bot.nick.lower()):
                    nicklen = len(self.bot.nick)
                    if len(text) > nicklen and text[nicklen] in [',', ':']:
                        self.trigger = text[nicklen + 1:]
            else:
                self.trigger = text
        else:
            if text.startswith('!'):
                self.trigger = text[1:]

    def reply(self, text, direct=False):
        if not self.bot:
            raise Exception('No bot object bound')

        if not self.reply_to and not self.source:
            raise Exception('Nobody to reply to')

        direct |= not bool(self.reply_to)
        recipient = self.source if direct else self.reply_to

        self.bot.privmsg(recipient, text)
