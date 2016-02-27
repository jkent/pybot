# -*- coding: utf-8 -*-
# vim: set ts=4 et

from datetime import datetime
import re


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
        self.trigger = False
        self.level = 0
        self.__dict__.update(parse_message(line))

        if self.cmd in ['PRIVMSG', 'NOTICE']:
            if self.param[0].startswith(('&', '#', '+', '!')):
                self.channel = self.param[0]
                self.reply_to = self.param[0]
            else:
                self.reply_to = self.source

    def reply(self, text, direct=False):
        if not self.bot:
            raise Exception('No bot object bound')

        if not self.reply_to and not self.source:
            raise Exception('Nobody to reply to')

        direct |= not bool(self.reply_to)
        recipient = self.source if direct else self.reply_to

        self.bot.privmsg(recipient, text)

