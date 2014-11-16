# -*- coding: utf-8 -*-
# vim: set ts=4 et

from core import Core

# bugfix/hack for lazy loaded modules in the plugin system
import email
import OpenSSL.SSL

if __name__ == '__main__':
    core = Core()
    core.add_bot()
    core.run()

