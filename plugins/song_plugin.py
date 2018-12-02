# -*- coding: utf-8 -*-
# vim: set ts=4 et

import os
import random
import sqlite3

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

    def on_unload(self, reload):
        self.db.close()

    def add_song(self, artist, title, nick=None):
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
            query = '''INSERT INTO track (artist_id, name, nick)
                       VALUES (?, ?, ?)'''
            self.cur.execute(query, (artist_id, title, nick))
        except:
            return False

        return True

    @level(1000)
    @hook
    def song_load_trigger(self, msg, args, argstr):
        try:
            filepath = os.path.join(self.bot.core.data_path, argstr)
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    artist, title = line.rsplit(' - ', 1)
                    self.add_song(artist, title)
            self.db.commit()
        except:
            msg.reply('failed to read file')
        return True

    @hook
    def song_trigger(self, msg):
        query = '''SELECT artist.name, track.name
                   FROM track
                   JOIN artist ON artist_id = artist.id
                   ORDER BY RANDOM()
                   LIMIT 1;'''
        self.cur.execute(query)
        artist, track = self.cur.fetchone()
        msg.reply('%s - %s' % (artist, track))