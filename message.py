# -*- coding: utf-8 -*-
# vim: set ts=4 et

from datetime import datetime
import re


message_re = re.compile(
  '^(?:'
    ':(?P<prefix>\\S+) '        +
  ')?'                          +
  '(?P<cmd>\\S+)'               +
  '(?:'                         +
    ' (?!:)(?P<param>.+?)'      +
  ')?'                          +
  '(?:'                         +
    ' :(?P<trailing>.+)'        +
  ')?$'
)

prefix_re =  re.compile(
  '^(?:'                        +
    '(?:'                       +
      '(?P<nick>[^.]+?)'        +
        '(?:'                   +
          '(?:'                 +
            '!(?P<user>.+?)'    +
          ')?'                  +
        '@(?P<host>.+)'         +
      ')?'                      +
    ')|(?P<server>.+)'          +
  ')$'
)


def parse_prefix(prefix):
    match = prefix_re.match(prefix)
    if match:
        return match.groupdict()
    else:
        return {'nick': None, 'user': None, 'host': None, 'server': None}

def parse_message(message):
    match = message_re.match(message)
    if match:
        d = match.groupdict()
    else:
        d = {'prefix': None, 'cmd': None, 'param': None, 'trailing': None}

    if d['prefix']:
        d.update(parse_prefix(d['prefix']))

    d['cmd'] = d['cmd'].upper()

    d['param'] = d['param'].split() if d['param'] else []

    if d['trailing']:
        d['param'].append(d['trailing'])
        d['trailing'] = True
    else:
        d['trailing'] = False

    return d


class Message(object):
    def __init__(self, line, bot=None):
        self.bot = bot
        self.raw = line
        self.reply_to = None
        self.time = datetime.utcnow()
        self.channel = None
        self.level = 0
        self.__dict__.update(parse_message(line))

        if self.cmd in ['PRIVMSG', 'NOTICE']:
            if self.param[0].startswith(('&', '#', '+', '!')):
                self.channel = self.param[0]
                self.reply_to = self.param[0]
            else:
                self.reply_to = self.nick

    def reply(self, text, direct=False):
        if not self.bot:
            raise Exception('No bot object bound')

        if not self.reply_to and not self.nick:
            raise Exception('Nobody to reply to')

        direct |= not bool(self.reply_to)
        recipient = self.nick if direct else self.reply_to

        self.bot.privmsg(recipient, text)

