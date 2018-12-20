# -*- coding: utf-8 -*-
# vim: set ts=4 et

import cgi
import requests
from six.moves.html_parser import HTMLParser

from plugin import *


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
        headers = {
            'User-Agent': 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Safari/537.36'
        }
        r = requests.get(url, stream=True, headers=headers)

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
