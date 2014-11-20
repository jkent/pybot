# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *
import config

from imgurpython import *

import re

client_id = config.imgur_client_id
client_secret = config.imgur_client_secret

url_re = re.compile(
  '(?:(?P<protocol>https?)://)?' +
  '(?:(?P<subdomain>\\w*)\\.)?imgur.com/' +
  '(?:gallery/)?(?:r/(?P<subreddit>\\w+)/)?(?P<id>\\w+)(?:\\.\\w+)?',
  re.I
)

class Plugin(BasePlugin):
    @hook
    def privmsg_command(self, msg):
        if not msg.channel:
            return

        m = url_re.match(msg.param[-1])
        if not m:
            return

        is_image = '.' in m.group(0)[-5:-3]
        print m.group(0)[-5:-4]

        client = ImgurClient(client_id, client_secret)

        if m.group('subreddit') != None:
            item = client.subreddit_image(m.group('subreddit'), m.group('id'))
        else:
            try:
                item = client.gallery_item(m.group('id'))
            except:
                item = client.get_image(m.group('id'))
  
        item_type = 'Album' if getattr(item, 'is_album', False) else 'Image'
        item_type = 'NSFW ' + item_type if item.nsfw else item_type

        if is_image:
            msg.reply('Gallery link: http://imgur.com/%s' % item.id)

        if item.title:
            msg.reply('%s: %s (%d)' % (item_type, item.title, getattr(item, 'score', -1)))
        else:
            msg.reply('%s: Untitled' % item_type)

