# -*- coding: utf-8 -*-
# vim: set ts=4 et

import os
import sys

if __name__ == '__main__':
    module = os.path.dirname(os.path.abspath(__file__))
    lib_path = os.path.abspath(os.path.join(module, '..', '..', 'lib'))
    third_party_path = os.path.join(lib_path, 'third-party')

    sys.path.insert(1, os.path.join(third_party_path, 'websocket-client'))
    sys.path.insert(1, os.path.join(third_party_path, 'python-slackclient'))

    from slackbridge import SlackBridge
    bridge = SlackBridge()
    bridge.run()
