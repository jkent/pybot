# -*- coding: utf-8 -*-
# vim: set ts=4 et

import os
import random
import re
import sqlite3
from traceback import print_exc

from plugin import *


class Plugin(BasePlugin):
    def on_load(self, reload):
        self.db = sqlite3.connect(os.path.join(self.bot.core.data_path, 'songs.db'))
        self.cur = self.db.cursor()
        query = '''CREATE TABLE IF NOT EXISTS artist (
                       id INTEGER PRIMARY KEY,
                       name TEXT,
                       UNIQUE(name)
                   );'''
        self.cur.execute(query)
        query = '''CREATE TABLE IF NOT EXISTS track (
                       id INTEGER PRIMARY KEY,
                       artist_id INTEGER,
                       name TEXT,
                       nick TEXT,
                       youtube TEXT,
                       UNIQUE(artist_id, name),
                       FOREIGN KEY(artist_id) REFERENCES artist(id)
                   );'''
        self.cur.execute(query)
        self.db.commit()

        self.last_track = {}

    def on_unload(self, reload):
        self.db.close()

    def add_track(self, artist, title, nick=None):
        track_added = False

        try:
            query = '''SELECT id FROM artist
                       WHERE name = ?'''
            self.cur.execute(query, (artist,))
            artist_id = self.cur.fetchone()[0]
        except:
            query = '''INSERT INTO artist (name)
                       VALUES (?);'''
            self.cur.execute(query, (artist,))
            artist_id = self.cur.lastrowid

        try:
            query = '''SELECT id FROM track
                       WHERE artist_id = ?, name = ?'''
            self.cur.execute(query, (artist_id, title))
            track_id = self.cur.fetchone()[0]
            track_exists = True
        except:
            query = '''INSERT INTO track (artist_id, name, nick)
                       VALUES (?, ?, ?)'''
            self.cur.execute(query, (artist_id, title, nick))
            track_id = self.cur.lastrowid
            track_added = True

        return track_id, track_added

    @hook
    def song_trigger(self, msg):
        query = '''SELECT artist.id, track.id, artist.name, track.name, track.youtube
                   FROM track
                   JOIN artist ON artist_id = artist.id
                   ORDER BY RANDOM()
                   LIMIT 1;'''
        self.cur.execute(query)
        artist_id, track_id, artist, track, youtube = self.cur.fetchone()
        if youtube:
            msg.reply('%s - %s - https://youtu.be/%s' % (artist, track, youtube))
        else:
            msg.reply('%s - %s' % (artist, track))

        self.last_track[msg.reply_to] = track_id

    @level(1000)
    @hook
    def song_load_trigger(self, msg, args, argstr):
        try:
            filepath = os.path.join(self.bot.core.data_path, argstr)
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    artist, title = line.rsplit(' - ', 1)
                    self.add_track(artist, title)
            self.db.commit()
        except:
            print_exc()
            msg.reply('failed to read file')
        return True

    @hook
    def song_add_trigger(self, msg, args, argstr):
        try:
            artist, title = argstr.strip().split(' - ', 1)
        except:
            msg.reply('Song must be in "artist - track" format')
            return True

        track_id, track_added = self.add_track(artist, title, msg.source)
        self.db.commit()

        self.last_track[msg.reply_to] = track_id

        if track_added:
            msg.reply('Song was added.')
        else:
            msg.reply("That song already exists!")

        return True

    @hook
    def song_who_trigger(self, msg):
        if not self.last_track.get(msg.reply_to):
            msg.reply('No last track.')
            return True

        query = '''SELECT nick FROM track
                   WHERE id = ?'''
        self.cur.execute(query, (self.last_track[msg.reply_to],))
        nick, = self.cur.fetchone()
        if not nick:
            nick = '(unknown)'

        msg.reply('Added by %s' % (nick,))
        return True

    @hook
    def song_youtube_trigger(self, msg, args, argstr):
        if not self.last_track.get(msg.reply_to):
            msg.reply('No last track.')
            return True

        pattern = '^(?:https?://)?(?:www\.)?(?:youtu\.be/|youtube\.com(?:/embed/|/v/|/watch\?v=))([\w-]{10,12})(?:&.*)?$'
        m = re.match(pattern, argstr.strip())
        if not m:
            msg.reply('That is not a valid youtube URL!')
            return True

        youtube_id = m.group(1)
        query = '''UPDATE track
                   SET youtube = ?
                   WHERE id = ?'''
        self.cur.execute(query, (youtube_id, self.last_track[msg.reply_to]))
        self.db.commit()
        return True

    @hook
    def song_youtube_delete_trigger(self, msg):
        if not self.last_track.get(msg.reply_to):
            msg.reply('No last track.')
            return True

        query = '''UPDATE track
                   SET youtube = NULL
                   WHERE id = ?'''
        self.cur.execute(query, (self.last_track[msg.reply_to],))
        self.db.commit()
        return True

    @hook
    def song_last_trigger(self, msg):
        msg.reply('%r' % (self.last_track.get(msg.reply_to),))
        return True