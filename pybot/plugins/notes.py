# -*- coding: utf-8 -*-
# vim: set ts=4 et

import os
import sqlite3

from plugin import *


class Plugin(BasePlugin):
    def on_load(self, reload):
        self.db = sqlite3.connect(os.path.join(self.bot.core.data_path, 'notes.db'))
        c = self.db.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS notes
                     (channel text, sender text, recipient text, message text)''')
        self.db.commit()

    def on_unload(self, reload):
        self.db.close()

    @hook
    def tell_trigger(self, msg, args, argstr):
        if not msg.channel:
            return

        data = {'channel': msg.param[0], 'sender': msg.source}
        data['recipient'], data['message'] = argstr.split(None, 1)

        c = self.db.cursor()
        c.execute('INSERT INTO notes VALUES (:channel, :sender, :recipient, :message)', data)
        self.db.commit()

        msg.reply("Aye aye Cap'n!")

    @hook
    def privmsg_command(self, msg):
        if not msg.channel:
            return

        c = self.db.cursor()
        criteria = {'channel': msg.param[0], 'recipient': msg.source}
        c.execute('SELECT sender, message FROM notes WHERE channel=:channel AND recipient=:recipient', criteria)
        rows = c.fetchall()
        if rows:
            for row in rows:
                msg.reply("Note: <%s> %s" % row)
            c.execute('DELETE FROM notes WHERE channel=:channel AND recipient=:recipient', criteria)
            self.db.commit()
