# -*- coding: utf-8 -*-
# vim: set ts=4 et

import bisect
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
            method = hook[3]
            nargs = method.__func__.__code__.co_argcount - 1
            try:
                method(*args[:nargs])
            except:
                print '%s hook error:' % hook[0]
                traceback.print_exc()

    @staticmethod
    def decorator(_type, transform=lambda x:x):
        def factory(*args):
            call = len(args) == 1 and hasattr(args[0], '__call__')
            def decorate(f):
                names = args if args and not call else (transform(f.__name__),)
                hooks = ((_type, name) for name in names)
                try:
                    f._hooks.update(hooks)
                except AttributeError:
                    f._hooks = Set(hooks)
                return f
            return decorate(args[0]) if call else decorate
        return factory

    def add(self, _type, desc, method, priority=100):
        #desc = tupleize_desc(desc)
        if not inspect.ismethod(method):
            raise Exception("Only instance methods may be hooked")
        hook = (_type, (desc,), priority, method)
        if debug:
            print 'new hook: %s' % repr(hook)
        bisect.insort(self.hooks, hook)

    def collect(self, instance):
        priority = getattr(instance, 'priority', 100)
        for _, method in inspect.getmembers(instance, inspect.ismethod):
            try:
                for _type, desc in method.__func__._hooks:
                    self.add(_type, desc, method, priority)
            except AttributeError:
                pass

    def remove(self, instance):
        if debug:
            for hook in (h for h in self.hooks if h[3].__self__ == instance):
                print 'removing hook: %s' % repr(hook)

        self.hooks = [h for h in self.hooks if h[3].__self__ != instance]

    def find(self, _type, desc):
        #desc = tupleize_desc(desc)
        i = bisect.bisect_right(self.hooks, (_type, (desc,)))
        j = bisect.bisect_left(self.hooks, (_type, (desc, None)))
        return self.hooks[i:j]

