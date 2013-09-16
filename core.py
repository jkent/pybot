# -*- coding: utf-8 -*-
# vim: set ts=4 et

import re, sys
import select
import time
import traceback
import config
from connection import RemoteServer
import plugin
from plugin import plugins


message_re = re.compile(
  '^(?:'
    ':(?P<prefix>\\S+) '        +
  ')?'                          +
  '(?P<command>\\S+)'           +
  '(?:'                         +
    ' (?!:)(?P<params>.+?)'     +
  ')?'                          +
  '(?:'                         +
    ' :(?P<trailing>.+)'        +
  ')?$'
)

prefix_re =  re.compile(
  '^(?:'                        +
    '(?:'                       +
      '(?P<nickname>[^.]+?)'    +
        '(?:'                   +
          '(?:'                 +
            '!(?P<user>.+?)'    +
          ')?'                  +
        '@(?P<host>.+)'         +
      ')?'                      +
    ')|(?P<servername>.+)'      +
  ')$'
)


def process_line(line):
    msg = {
        'raw': line,
        'prefix': None, 'command': None, 'params': None, 'trailing': None,
        'servername': None, 'nickname': None, 'user': None, 'host': None,
        'reply': None
    }

    match = message_re.match(line)
    if match:
        msg.update(match.groupdict())

    if msg['prefix']:
        match = prefix_re.match(msg['prefix'])
        if match:
            msg.update(match.groupdict())

    if msg['params']:
        msg['params'] = msg['params'].split(' ')

    if msg['command'] in ['PRIVMSG', 'NOTICE']:
        if msg['params'][0].startswith(('&', '#', '+', '!')):
            msg['reply'] = msg['params'][0]
        else:
            msg['reply'] = msg['nickname']   

    plugin.event('message', msg)


def tick():
    global selectables
    global time_last

    time_now = time.time()
    if time_last + 1 <= time_now:
        time_last = time_now
        for obj in selectables:
            obj.on_tick(time_now)
        plugin.event('tick', time_now)

    try_read = []
    try_write = []

    for obj in selectables:
        if obj.fileno() == None:
            continue
        if obj.can_read():
            try_read.append(obj)
        if obj.can_write():
            try_write.append(obj)

    readable, writeable, _ = select.select(try_read, try_write, [], 0.5)

    for obj in writeable:
        obj.do_write()
    for obj in readable:
        obj.do_read()


def run():
    global client
    global selectables
    global connected, running, in_shutdown
    global time_last

    client = RemoteServer(config.host, config.ssl)
    client.process_line = process_line

    for name in config.autoload_plugins:
        plugin.load(name, client)

    client.connect()

    selectables = [client]
    time_last = time.time()

    in_shutdown = False
    running = True
    connected = False
    while running:
        try:
            tick()
        except KeyboardInterrupt:
            shutdown('KeyboardInterrupt')
        if client.connected and not connected:
            plugin.event('connect')
            connected = True
        if not client.connected and connected:
            plugin.event('disconnect')
            connected = False
        if in_shutdown and not connected:
            running = False


def shutdown(reason=''):
    global client
    global running, in_shutdown

    if client.connected:
        client.write('QUIT :%s' % reason)
        client.do_write()

    if in_shutdown:
        running = False

    in_shutdown = True

