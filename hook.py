# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
from contextlib import contextmanager
import inspect
import traceback

import config

debug = 'hook' in config.debug


class Hooks:
    def __init__(self):
        self.hooks = []

    @staticmethod
    def call(hooks, *args):
        for hook in hooks:
            if debug:
                print('calling hook: %s' % repr(hook))
            fn = hook[3]
            if inspect.ismethod(fn):
                nargs = fn.__func__.__code__.co_argcount - 1
            else:
                nargs = fn.__code__.co_argcount
            try:
                if fn(*args[:nargs]):
                    return True
            except:
                print('%s hook error:' % hook[0])
                traceback.print_exc()

    @staticmethod
    def create(fn, _type, desc, priority=500, data=None):
        if data == None:
            data = {}
        if not callable(fn):
            raise Exception('fn must be callable')
        hook = (_type, [desc,], priority, fn, data)
        return hook

    @contextmanager
    def modify(self, hook):
        self.uninstall(hook, True)
        yield hook
        self.install(hook, True)

    def install(self, hook, modify=False):
        i = bisect.bisect_left(self.hooks, hook)
        if i < len(self.hooks) and self.hooks[i] == hook:
            raise Exception('hook already installed')
        self.hooks.insert(i, hook)
        if debug and not modify:
            print('installed hook: %s' % repr(hook))

    def uninstall(self, hook, modify=False):
        i = bisect.bisect_left(self.hooks, hook)
        if i >= len(self.hooks) or self.hooks[i] != hook:
            raise Exception('hook not installed')
        if not modify:
            data = hook[4]
            fn = data.get('uninstall', None)
            if fn: fn(hook)
        del self.hooks[i]
        if debug and not modify:
            print('uninstalled hook: %s' % repr(hook))

    def find(self, _type, left, right=None):
        if right == None:
            right = left
        i = bisect.bisect_left(self.hooks, (_type, [left,]))
        j = bisect.bisect_right(self.hooks, (_type, [right, None]))
        return self.hooks[i:j]

