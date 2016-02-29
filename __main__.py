# -*- coding: utf-8 -*-
# vim: set ts=4 et

import os, sys
from core import Core

if __name__ == '__main__':
    root = os.path.dirname(os.path.abspath(__file__))
    lib_path = os.path.abspath(os.path.join(root, 'lib'))
    third_party_path = os.path.join(lib_path, 'third-party')

    for name in os.listdir(third_party_path):
        path = os.path.join(third_party_path, name)
        if os.path.isdir(path):
            if not os.path.exists(os.path.join(path, '__init__.py')):
                sys.path.insert(1, path)
        elif path.endswith('.egg'):
            sys.path.insert(1, path)
    sys.path.insert(1, third_party_path)
    sys.path.insert(1, lib_path)

    core = Core()
    core.add_bot()
    core.run()

