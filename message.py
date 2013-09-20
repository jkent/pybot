# -*- coding: utf-8 -*-
# vim: set ts=4 et

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

class Message(object):
    def __init__(self, line, bot=None):
        self.bot = bot
        self.raw = line
        self.prefix = None
        self.cmd = None
        self.param = None
        self.trailing = None
        self.server = None
        self.nick = None
        self.user = None
        self.host = None
        self.reply_to = None        

        match = message_re.match(self.raw)
        if match:
            self.__dict__.update(match.groupdict())

        if self.prefix:
            match = prefix_re.match(self.prefix)
            if match:
                self.__dict__.update(match.groupdict())

        self.cmd = self.cmd.upper()

        if self.param:
            self.param = self.param.split()
        else:
            self.param = []
        
        if self.trailing:
            self.param.append(self.trailing)
            self.trailing = True
        else:
            self.trailing = False

        if self.cmd in ['PRIVMSG', 'NOTICE']:
            if self.param[0].startswith(('&', '#', '+', '!')):
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

