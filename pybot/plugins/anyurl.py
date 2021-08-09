# -*- coding: utf-8 -*-
# vim: set ts=4 et

import cgi
from html.parser import HTMLParser
import re
import requests

from pybot import config
from pybot.plugin import *


content_types = (
    'text/html',
    'text/xml',
    'application/xhtml+xml',
    'application/xml'
)

class TitleParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.match = False
        self.title = ''


    def handle_starttag(self, tag, attrs):
        if tag == 'meta':
            og_title = False
            for attr in attrs:
                if attr == ('property', 'og:title'):
                    og_title = True
            if og_title:
                for attr in attrs:
                    if attr[0] == 'content':
                        self.title = attr[1]

        self.match = True if not self.title and tag == 'title' else False


    def handle_data(self, data):
        if self.match:
            self.title = data.strip()
            self.match = False


class Plugin(BasePlugin):
    default_priority = 1

    @hook
    def any_url(self, msg, domain, url):
        blacklist = self.config.get('blacklist')
        if blacklist:
            for regex in blacklist:
                if re.match(regex, url, re.IGNORECASE):
                    return

        default_ua = 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; " \
                "compatible; pybot/1.0.3; +https://github.com/jkent/pybot) " \
                "Safari/537.36'
        user_agent = config.config[self.bot.network].get('plugins', {}) \
                .get('anyurl', {}).get('user-agent', default_ua)

        headers = {
            'User-Agent': user_agent
        }

        try:
            r = requests.get(url, stream=True, headers=headers, timeout=10)
        except requests.exceptions.ReadTimeout:
            msg.reply('URL Timeout')
            return

        content_type, params = cgi.parse_header(r.headers['Content-Type'])
        if not content_type in content_types:
            return

        r.encoding = 'utf-8'
        if 'charset' in params:
            r.encoding = params['charset'].strip("'\"")

        parser = TitleParser()

        for line in r.iter_lines(chunk_size=1024, decode_unicode=True):
            parser.feed(line)
            if parser.title:
                break

        msg.reply('\x031,0URL\x03 %s' % parser.title)
