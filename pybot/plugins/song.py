# -*- coding: utf-8 -*-
# vim: set ts=4 et

import os
import re
import sqlite3
from traceback import print_exc

from plugin import *


KEEP_RATIO = 0.1


class Plugin(BasePlugin):
    def on_load(self, reload):
        self.db = sqlite3.connect(os.path.join(self.bot.core.data_path, 'song.db'))
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
        query = '''CREATE TRIGGER IF NOT EXISTS delete_unused_artist
                   AFTER DELETE ON track
                   BEGIN
                       DELETE FROM artist WHERE id = OLD.artist_id AND
                       (SELECT COUNT(*) FROM track WHERE artist_id = OLD.artist_id) = 0;
                   END;'''
        self.cur.execute(query)
        self.db.commit()

        self.last_tracks = {}


    def on_unload(self, reload):
        self.db.close()


    def add_track(self, artist, title, nick=None):
        track_added = False

        query = '''SELECT id FROM artist
                    WHERE name = ? COLLATE NOCASE;'''
        self.cur.execute(query, (artist,))
        row = self.cur.fetchone()
        if row is not None:
            artist_id, = row
        else:
            query = '''INSERT INTO artist (name)
                    VALUES (?);'''
            self.cur.execute(query, (artist,))
            artist_id = self.cur.lastrowid

        query = '''SELECT id FROM track
                    WHERE artist_id = ? AND name = ? COLLATE NOCASE;'''
        self.cur.execute(query, (artist_id, title))
        row = self.cur.fetchone()
        if row is not None:
            track_id, = row
        else:
            query = '''INSERT INTO track (artist_id, name, nick)
                       VALUES (?, ?, ?);'''
            self.cur.execute(query, (artist_id, title, nick))
            track_id = self.cur.lastrowid
            track_added = True

        return track_id, track_added


    @hook
    def song_trigger(self, msg, args, argstr):
        context = msg.reply_to
        if argstr:
            msg.reply('Unknown command, see help.')
            return

        while True:
            query = '''SELECT track.id, artist.name, track.name, track.youtube
                    FROM track
                    JOIN artist ON artist_id = artist.id
                    ORDER BY RANDOM()
                    LIMIT 1;'''
            self.cur.execute(query)
            row = self.cur.fetchone()
            if row is None:
                msg.reply('No songs yet!')
                return

            track_id, artist, track, youtube = row

            if context not in self.last_tracks or track_id not in self.last_tracks[context]:
                break

        if youtube is not None:
            msg.reply('%s - %s - https://youtu.be/%s' % (artist, track, youtube))
        else:
            msg.reply('%s - %s' % (artist, track))

        query = '''SELECT COUNT(*)
                   FROM track;'''
        self.cur.execute(query)
        count, = self.cur.fetchone()
        keep = int(count * KEEP_RATIO)

        if context not in self.last_tracks:
            self.last_tracks[context] = []
        self.last_tracks[context].append(track_id)
        self.last_tracks[context] = self.last_tracks[context][-keep:]


    @hook
    def song_add_trigger(self, msg, args, argstr):
        context = msg.reply_to
        try:
            artist, title = argstr.strip().split(' - ', 1)
        except:
            msg.reply('Song must be in "artist - track" format')
            return True

        track_id, track_added = self.add_track(artist, title, msg.source)
        print(track_id, track_added)
        self.db.commit()

        query = '''SELECT COUNT(*)
                   FROM track;'''
        self.cur.execute(query)
        count, = self.cur.fetchone()
        keep = int(count * KEEP_RATIO)

        if context not in self.last_tracks:
            self.last_tracks[context] = []
        self.last_tracks[context].append(track_id)
        self.last_tracks[context] = self.last_tracks[context][-keep:]

        if track_added:
            msg.reply('Song was added.')
        else:
            msg.reply("That song already exists!")

        return True


    @level(900)
    @hook
    def song_delete_trigger(self, msg):
        context = msg.reply_to
        if not self.last_tracks.get(context):
            msg.reply('No last track.')
            return True

        track_id = self.last_tracks[context][-1]

        query = '''DELETE FROM track
                   WHERE id = ?;'''
        self.cur.execute(query, (track_id,))
        self.db.commit()


        del self.last_tracks[context][-1]

        msg.reply('Song deleted')
        return True


    @hook
    def song_fix_artist_trigger(self, msg, args, argstr):
        context = msg.reply_to
        if self.last_tracks.get(context) is None:
            msg.reply('No last track.')
            return True

        track_id = self.last_tracks[context][-1]

        query = '''SELECT artist.id, artist.name
                   FROM track
                   JOIN artist ON artist_id = artist.id
                   WHERE track.id = ?;'''
        self.cur.execute(query, (track_id,))
        row = self.cur.fetchone()
        original_artist_id, original_artist_name = row

        if original_artist_name == argstr:
            msg.reply('No change.')
            return True

        query = '''SELECT id
                   FROM artist
                   WHERE name = ?
                   LIMIT 1;'''
        self.cur.execute(query, (argstr,))
        row = self.cur.fetchone()
        if row:
            artist_id, = row
            query = '''UPDATE track
                       SET artist_id = ?
                       WHERE id = ?;'''
            self.cur.execute(query, (artist_id, track_id))

            query = '''SELECT COUNT(*)
                       FROM track
                       WHERE artist_id = ?;'''
            self.cur.execute(query, (original_artist_id,))
            row = self.cur.fetchone()
            count, = row

            if count == 0:
                query = '''DELETE FROM artist
                           WHERE id = ?;'''
                self.cur.execute(query, (original_artist_id,))
        else:
            query = '''UPDATE artist
                       SET name = ?
                       WHERE id = ?;'''
            self.cur.execute(query, (argstr, original_artist_id))

        msg.reply('Artist updated.')
        return True


    @hook
    def song_fix_title_trigger(self, msg, args, argstr):
        context = msg.reply_to
        if not self.last_tracks.get(context):
            msg.reply('No last track.')
            return True

        track_id = self.last_tracks[context][-1]

        query = '''SELECT name
                   FROM track
                   WHERE id = ?;'''
        self.cur.execute(query, (track_id,))
        row = self.cur.fetchone()
        original_track_name, = row

        if original_track_name == argstr:
            msg.reply('No change.')
            return True

        query = '''UPDATE track
                   SET name = ?
                   WHERE id = ?;'''
        self.cur.execute(query, (argstr, track_id))
        self.db.commit()

        msg.reply('Title updated.')
        return True


    @hook
    def song_last_trigger(self, msg):
        context = msg.reply_to
        if not self.last_tracks.get(context):
            msg.reply('No last track.')
            return True

        track_id = self.last_tracks[context][-1]

        query = '''SELECT track.id, artist.name, track.name, track.youtube
                   FROM track
                   JOIN artist ON artist_id = artist.id
                   WHERE track.id = ?;'''
        self.cur.execute(query, (track_id,))
        row = self.cur.fetchone()

        track_id, artist, track, youtube = row
        if youtube is not None:
            msg.reply('%s - %s - https://youtu.be/%s' % (artist, track, youtube))
        else:
            msg.reply('%s - %s' % (artist, track))

        return True


    @level(1000)
    @hook
    def song_load_trigger(self, msg, args, argstr):
        try:
            count = 0
            filepath = os.path.join(self.bot.core.data_path, argstr)
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    parts = line.split(' - ', 2)
                    artist, title, nick = map(str.strip, parts)
                    _, sucess = self.add_track(artist, title, nick)
                    if sucess:
                        count += 1
            self.db.commit()
        except:
            print_exc()
            msg.reply('Failed to read file.')
            return True

        msg.reply('Loaded %d songs sucessfully.' % (count,))
        return True


    @hook
    def song_search_trigger(self, msg, args, argstr):
        context = msg.reply_to
        query = '''SELECT track.id, track.youtube, artist.name || ' - ' || track.name AS song
                   FROM track
                   JOIN artist ON artist_id = artist.id
                   WHERE song LIKE ?
                   ORDER BY RANDOM()
                   LIMIT 5;'''
        self.cur.execute(query, ('%%%s%%' % (argstr,),))
        rows = self.cur.fetchall()
        if not rows:
            msg.reply('No tracks found.')
            return True

        for row in rows:
            track_id, youtube, song = row
            if youtube is not None:
                msg.reply('%s - https://youtu.be/%s' % (song, youtube))
            else:
                msg.reply(song)

        query = '''SELECT COUNT(*)
                   FROM track;'''
        self.cur.execute(query)
        count, = self.cur.fetchone()
        keep = int(count * KEEP_RATIO)

        if context not in self.last_tracks:
            self.last_tracks[context] = []
        self.last_tracks[context].append(track_id)
        self.last_tracks[context] = self.last_tracks[context][-keep:]

        return True


    @hook
    def song_stats_trigger(self, msg):
        query = '''SELECT COUNT(*)
                   FROM artist;'''
        self.cur.execute(query)
        artist_count, = self.cur.fetchone()

        query = '''SELECT COUNT(*)
                   FROM track;'''
        self.cur.execute(query)
        track_count, = self.cur.fetchone()

        msg.reply('There are %d artists with %d tracks.' % (artist_count, track_count))
        return True


    @hook
    def song_who_trigger(self, msg):
        context = msg.reply_to
        if not self.last_tracks.get(context):
            msg.reply('No last track.')
            return True

        track_id = self.last_tracks[context][-1]

        query = '''SELECT nick FROM track
                   WHERE id = ?;'''
        self.cur.execute(query, (track_id,))
        nick, = self.cur.fetchone()
        if not nick:
            nick = 'anonymous'

        msg.reply('Added by %s' % (nick,))
        return True


    @hook
    def song_youtube_trigger(self, msg, args, argstr):
        context = msg.reply_to
        if not self.last_tracks.get(context):
            msg.reply('No last track.')
            return True

        pattern = '^(?:https?://)?(?:www\.)?(?:youtu\.be/|youtube\.com(?:/embed/|/v/|/watch\?v=))([\w-]{10,12})(?:&.*)?$'
        m = re.match(pattern, argstr.strip())
        if not m:
            msg.reply('That is not a valid youtube URL!')
            return True

        track_id = self.last_tracks[context][-1]

        youtube_id = m.group(1)
        query = '''UPDATE track
                   SET youtube = ?
                   WHERE id = ?;'''
        self.cur.execute(query, (youtube_id, track_id))
        self.db.commit()
        msg.reply('Youtube link set!')
        return True


    @level(900)
    @hook
    def song_youtube_delete_trigger(self, msg):
        context = msg.reply_to
        if not self.last_tracks.get(context):
            msg.reply('No last track.')
            return True

        track_id = self.last_tracks[context][-1]

        query = '''UPDATE track
                   SET youtube = NULL
                   WHERE id = ?;'''
        self.cur.execute(query, (track_id,))
        self.db.commit()
        return True
