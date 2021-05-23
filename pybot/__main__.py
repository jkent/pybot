# -*- coding: utf-8 -*-
# vim: set ts=4 et

from .core import Core

def main():
    core = Core()
    core.add_bot('undergnd')
    core.run()

if __name__ == '__main__':
    main()
