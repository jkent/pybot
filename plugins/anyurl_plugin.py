# -*- coding: utf-8 -*-
# vim: set ts=4 et

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
            self.title = data
            self.match = False


class Plugin(BasePlugin):
    default_priority = 1
    
    @hook
    def any_url(self, msg, domain, url):
        r = requests.get(url, stream=True)
        
        if not r.headers['Content-Type'].startswith(content_types):   
            return

        parser = TitleParser()

        for line in r.iter_lines(chunk_size=1024, decode_unicode=True):
            parser.feed(line)
            if parser.title:
                break

        msg.reply('\x031,0URL\x03 %s' % parser.title)
