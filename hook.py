# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
from contextlib import contextmanager
import inspect
from sets import Set
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
                print 'calling hook: %s' % repr(hook)
            fn = hook[3]
            if inspect.ismethod(fn):
                nargs = fn.__func__.__code__.co_argcount - 1
            else:
                nargs = fn.__code__.co_argcount
            try:
                if fn(*args[:nargs]):
                    return True
            except:
                print '%s hook error:' % hook[0]
                traceback.print_exc()

    @staticmethod
    def create(fn, _type, desc, priority=100, data=None):
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
            print 'installed hook: %s' % repr(hook)

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
            print 'uninstalled hook: %s' % repr(hook)

    def find(self, _type, left, right=None):
        if right == None:
            right = left
        i = bisect.bisect_left(self.hooks, (_type, [left,]))
        j = bisect.bisect_right(self.hooks, (_type, [right, None]))
        return self.hooks[i:j]

def hook(*args):
    call = len(args) == 1 and hasattr(args[0], '__call__')
    def decorate(f):
        if call or not args:
            try:
                name, _type = f.__name__.lstrip('_').rsplit('_', 1)
            except:
                raise ValueError("function name must follow <hookname>_<hooktype> convention")
            hooks = ((_type, name.replace('_', ' ')),)
        elif len(args) == 1:
            try:
                _, _type = f.__name__.rsplit('_', 1)
            except:
                raise ValueError("function name must follow anything_<hooktype> convention")
            if isinstance(args[0], basestring):
                hooks = ((_type, args[0]),)
            elif all(isinstance(s, basestring) for s in args[0]):
                hooks = ((_type, s) for s in args[0])
            else:
                raise TypeError("name is not a string or iterable of strings")
        elif len(args) == 2:
            if not isinstance(args[0], basestring):
                raise TypeError("type is not a string")
            _type = args[0]
            if isinstance(args[1], basestring):
                hooks = ((_type, args[1]),)
            elif all(isinstance(s, basestring) for s in args[1]):
                hooks = ((_type, s) for s in args[1])
            else:
                raise TypeError("name is not a string or iterable of strings")
        else:
            raise TypeError("too many arguments provided")
        try:
            f._hooks.update(hooks)
        except AttributeError:
            f._hooks = Set(hooks)
        return f
    return decorate(args[0]) if call else decorate

