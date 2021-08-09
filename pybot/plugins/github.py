# -*- coding: utf-8 -*-
# vim: set ts=4 et

import re
import requests

from pybot.plugin import *


url_re = re.compile(r'^https?://(?:www\.)?github.com/(?P<user>[a-zA-Z0-9_-]+)(?:/(?P<repo>[a-zA-Z0-9_-]+)(?:.git)?)?/?$')
repo_api_url = 'https://api.github.com/repos/{user}/{repo}'
commits_api_url = 'https://api.github.com/repos/{user}/{repo}/commits?per_page=1'
user_api_url = 'https://api.github.com/users/{user}'


def get_json_data(url, **kwargs):
    r = requests.get(url.format(**kwargs))

    if r.status_code not in [200, 301, 304]:
        return None

    return r.json()


class Plugin(BasePlugin):
    @hook('www.github.com')
    @hook('github.com')
    def github_url(self, msg, domain, url):
        if not msg.channel:
            return

        m = re.match(url_re, url)
        if not m:
            print('no match')
            return

        user = m.group('user')
        repo = m.group('repo')

        if repo:
            data = get_json_data(repo_api_url, user=user, repo=repo)
            if not data:
                return
            msg.reply('\x031,0GitHub\x03 %s' % (data['description'],))

            data = get_json_data(commits_api_url, user=user, repo=repo)
            if not data:
                return
            msg.reply('Last commit: %s' % (data[0]['commit']['message'],))
        else:
            data = get_json_data(user_api_url, user=user)
            if not data:
                return
            msg.reply('\x031,0GitHub\x03 %s: %d repos, %d gists' % (data['name'], data['public_repos'], data['public_gists']))
