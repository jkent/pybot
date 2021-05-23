# -*- coding: utf-8 -*-
# vim: set ts=4 et

import re
import requests
import tweepy
from html.parser import HTMLParser

from pybot.plugin import *


def tweet_cleaner(text):
    hp = HTMLParser()
    return hp.unescape(text.replace('\n', ' ').replace('\r', ''))

def url_expander(sentence, msg):
    regex_tco = re.compile(r'https?://t.co/.*')
    urls = []
    words = sentence.split()

    for word in words:
        m = re.match(regex_tco, word)

        if m:
            idx = words.index(word)
            r = requests.get(word)

            if r.status_code in [200, 301, 302]:
                msg.reply(r.url)


class Plugin(BasePlugin):
    def on_load(self, reloading):
        apik = config.config[self.bot.network].get('twitter', {}) \
                .get('apikey')
        apis = config.config[self.bot.network].get('twitter', {}) \
                .get('secret')
        autht = config.config[self.bot.network].get('twitter', {}) \
                .get('auth_token')
        authts = config.config[self.bot.network].get('twitter', {}) \
                .get('auth_secret')

        auth = tweepy.OAuthHandler(apik, apis)
        auth.set_access_token(autht, authts)
        self._api = tweepy.API(auth)


    @hook('twitter.com')
    def twitter_url(self, msg, args, argstr):
        regx = re.compile(r'https?://twitter.com/[a-zA-Z0-9_\-]+/status/' \
                r'(?P<id>[0-9]+)')
        m = re.match(regx, argstr)

        if not m:
            return
        else:
            twitter_id = m.group('id')

        try:
            status = self._api.get_status(twitter_id, tweet_mode='extended')
            msg.reply(tweet_cleaner(status.full_text))
            url_expander(status.full_text, msg)

        except tweepy.TweepError as e:
            msg.reply('No Status for that ID.')

        return True

    @hook
    def twitter_user_trigger(self, msg, args, argstr):
        try:
            user = self._api.get_user(argstr, tweet_mode='extended')
            msg.reply(tweet_cleaner(user.status.full_text))
            url_expander(user.status.full_text, msg)

        except tweepy.TweepError as e:
            print(e)
            msg.reply('No user by that name.')

    @hook
    def twitter_help_trigger(self, msg, args, argstr):
        msg.reply('Usage: twitter [search|user] <text> Returns most recent ' \
            'or specified by URL Tweet text.')

    @hook
    def twitter_search_trigger(self, msg, args, argstr):
        try:
            cursor = tweepy.Cursor(self._api.search, q=argstr, rpp=1,
                    tweet_mode='extended')

            for c in cursor.items(1):
                uname = c.author.name
                msg.reply('@{0}: {1}'.format(uname, tweet_cleaner(c.full_text)))
                url_expander(c.full_text, msg)
                break

            else:
                msg.reply('No results.')

        except tweepy.TweepError as e:
            print(e)
            msg.reply('Update failed.')
