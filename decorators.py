# -*- coding: utf-8 -*-
# vim: set ts=4 et

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
            if isinstance(args[0], str):
                hooks = ((_type, args[0]),)
            elif all(isinstance(s, str) for s in args[0]):
                hooks = ((_type, s) for s in args[0])
            else:
                raise TypeError("name is not a string or iterable of strings")
        elif len(args) == 2:
            if not isinstance(args[0], str):
                raise TypeError("type is not a string")
            _type = args[0]
            if isinstance(args[1], str):
                hooks = ((_type, args[1]),)
            elif all(isinstance(s, str) for s in args[1]):
                hooks = ((_type, s) for s in args[1])
            else:
                raise TypeError("name is not a string or iterable of strings")
        else:
            raise TypeError("too many arguments provided")
        try:
            f._hooks.update(hooks)
        except AttributeError:
            f._hooks = set(hooks)
        return f
    return decorate(args[0]) if call else decorate

def priority(value):
    if not isinstance(value, int):
        raise Exception("priority decorator requires an integer value")
    def decorate(f):
        f._priority = value
        return f
    return decorate

def level(value):
    if not isinstance(value, int):
        raise Exception("level decorator requires an integer value")
    def decorate(f):
        f._level = value
        return f
    return decorate

