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

    def add(self, _type, desc, method, priority=100, data=None):
        if not inspect.ismethod(method):
            raise Exception("Only instance methods may be hooked")
        hook = (_type, [desc,], priority, method, data)
        if debug:
            print 'new hook: %s' % repr(hook)
        bisect.insort(self.hooks, hook)
        return hook

    def resort(self, hook):
        self.hooks.remove(hook)
        bisect.insort(self.hooks, hook)

    def remove(self, hook):
        if debug:
            print 'removing hook: %s' % repr(hook)

        try:
            self.hooks.remove(hook)
        except:
            pass

    def remove_instance_hooks(self, instance):
        if debug:
            for hook in (h for h in self.hooks if h[3].__self__ == instance):
                print 'removing hook: %s' % repr(hook)

        self.hooks = [h for h in self.hooks if h[3].__self__ != instance]

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
            if isinstance(arg[0], basestring):
                hooks = ((_type, arg[0]),)
            elif all(isinstance(s, basestring) for s in arg[0]):
                hooks = ((_type, s) for s in arg[0])
            else:
                raise TypeError("name is not a string or iterable of strings")
        elif len(args) == 2:
            if not isinstance(arg[0], basestring):
                raise TypeError("type is not a string")
            _type = arg[0]
            if isinstance(arg[1], basestring):
                hooks = ((_type, arg[1]),)
            elif all(isinstance(s, basestring) for s in arg[1]):
                hooks = ((_type, s) for s in arg[1])
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

