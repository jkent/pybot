#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Expression parser and compiler."""

import string
import inspect
import re
import collections
import math
import random

TOKEN_NUM = 1
TOKEN_VAR = 2
TOKEN_FUNC = 4
TOKEN_OP_RTL = 8
TOKEN_OP_LTR = 16
TOKEN_LPAREN = 32
TOKEN_RPAREN = 64

TOKEN_OPERATOR = TOKEN_OP_RTL | TOKEN_OP_LTR | TOKEN_LPAREN
TOKEN_VALUE = TOKEN_NUM | TOKEN_VAR | TOKEN_FUNC | TOKEN_RPAREN

OPS_RTL = {
    '~':  (7, lambda a: lambda env: ~a(env)),
}

OPS_LTR = {
    '**': (8, lambda a, b: lambda env: a(env) ** b(env)),
    '*':  (6, lambda a, b: lambda env: a(env) *  b(env)),
    '/':  (6, lambda a, b: lambda env: a(env) /  b(env)),
    '%':  (6, lambda a, b: lambda env: a(env) %  b(env)),
    '+':  (5, lambda a, b: lambda env: a(env) +  b(env)),
    '-':  (5, lambda a, b: lambda env: a(env) -  b(env)),
    '<<': (4, lambda a, b: lambda env: a(env) << b(env)),
    '>>': (4, lambda a, b: lambda env: a(env) >> b(env)),
    '&':  (3, lambda a, b: lambda env: a(env) &  b(env)),
    '^':  (2, lambda a, b: lambda env: a(env) ^  b(env)),
    '|':  (1, lambda a, b: lambda env: a(env) |  b(env)),
}

OPS = OPS_RTL.copy()
OPS.update(OPS_LTR)

BUILTIN_FUNCS = {
    'abs': {'nreq': 1, 'func': abs, 'desc': 'Absolute value'},
    'bin': {'nreq': 1, 'func': bin, 'desc': 'Binary notation'},
    'conjugate': {'func': lambda x: x.conjugate()},
    'dec': {'nreq': 1, 'func': int, 'desc': 'Decimal notation'},
    'imag': {'func': lambda x: x.imag, 'desc': 'Imaginary portion of number'},
    'int': {'nreq': 1, 'func': int, 'desc': 'Cast to integer'},
    'float': {'nreq': 1, 'func': float, 'desc': 'Cast to floating point'},
    'ceil': {'nreq': 1, 'func': math.ceil, 'desc': 'Round up'},
    'cos': {'nreq': 1, 'func': math.cos, 'desc': 'Trig cosine function'},
    'factorial': {'nreq': 1, 'func': math.factorial},
    'floor': {'nreq': 1, 'func': math.floor, 'desc': 'Round down'},
    'hex': {'nreq': 1, 'func': hex, 'desc': 'Hex notation'},
    'log': {'nreq': (1, 2), 'func': math.log, 'desc': 'Logarithm, second argument is base'},
    'log10': {'nreq': 1, 'func': math.log10, 'desc': 'Base 10 logarithm'},
    'oct': {'nreq': 1, 'func': oct, 'desc': 'Octal notation'},
    'round': {'nreq': (1, 2), 'func': round, 'desc': 'Normal round, second argument is number of decimal places'},
    'sin': {'nreq': 1, 'func': math.sin, 'desc': 'Trig sine function'},
    'sqrt': {'nreq': 1, 'func': math.sqrt, 'desc': 'Square root function'},
    'tan': {'nreq': 1, 'func': math.tan, 'desc': 'Trig tangent function'},
    'rand': {'nreq': 0, 'func': random.random, 'desc': 'Random number between 0 and 1'},
    'randint': {'func': random.randint, 'desc': 'Random integer between first and second arguments, inclusive'},
    'real': {'func': lambda x: x.real, 'desc': 'Real portion of number'},
}

BUILTIN_VARS = {
    'pi': math.pi,
    'e': math.e,
}


class ExpressionError(Exception):
    """Exceptoion base for all expression exceptions."""
    def __init__(self, pos, message):
        super(ExpressionError, self).__init__(message)
        self.pos = pos

class ParseError(ExpressionError):
    """Exception that is thrown during expression parsing."""
    def __init__(self, pos, message):
        super(ParseError, self).__init__(pos, message)

class CompileError(ExpressionError):
    """Exception that is thrown during expression compliation."""
    def __init__(self, pos, message):
        super(CompileError, self).__init__(pos, message)

class ComputeError(ExpressionError):
    """Exception that is thrown during expression computation."""
    def __init__(self, pos, message):
        super(ComputeError, self).__init__(pos, message)

class DeclarationError(Exception):
    """Exception that is thrown during func declaration."""
    def __init__(self, message):
        super(DeclarationError, self).__init__(message)


def issymbol(s):
    """Validates a string as a symbol."""

    if not s:
        return False

    if s[0] not in string.letters + '_':
        return False

    for c in s[1:]:
        if c not in string.digits + string.letters + '_':
            return False

    return True


def parse_expr(expr, offset=0):
    """Expression parser that returns a tuple of tokens."""

    tokens = []
    pos = 0
    paren = 0
    token_start = None
    last = 0

    def add_value():
        """Adds a value type (except for func) to the tokens list."""

        token = expr[token_start:pos]
        if not token:
            return last

        if issymbol(token):
            type_ = TOKEN_VAR

        else:
            try:
                if 'j' in token:
                    token = complex(token)
                elif '.' in token or 'e' in token:
                    token = float(token)
                elif 'x' in token or 'b' in token or \
                    (len(token) > 1 and token[0] == '0'):
                    int(token, 0)
                else:
                    token = int(token)
                type_ = TOKEN_NUM

            except ValueError:
                raise ParseError(offset + token_start, 'invalid token')

        if last & ~TOKEN_OPERATOR:
            raise ParseError(offset + token_start, 'operator expected')

        tokens.append((type_, token, offset + token_start))
        return type_

    def add_func(pos):
        """Adds a func type to the tokens list."""

        if last & ~TOKEN_OPERATOR:
            raise ParseError(offset + token_start, 'operator expected')

        name = expr[token_start:pos]
        if not issymbol(name):
            raise ParseError(offset + token_start, 'invalid func name')

        args = []
        pos += 1
        start = pos
        paren = 1
        while pos < len(expr):
            if expr[pos] == '(':
                paren += 1

            elif expr[pos] == ',':
                if paren == 1:
                    subexpr = expr[start:pos]
                    args.append(parse_expr(subexpr, offset + start))
                    pos += 1
                    while pos < len(expr):
                        if expr[pos] != ' ':
                            break
                        pos += 1
                    start = pos
                    continue

            elif expr[pos] == ')':
                paren -= 1
                if paren == 0:
                    subexpr = expr[start:pos]
                    if args or subexpr.strip():
                        args.append(parse_expr(subexpr, offset + start))
                    pos += 1
                    break

            pos += 1

        if paren > 0:
            raise ParseError(offset + pos, 'closing parenthesis expected')

        tokens.append((TOKEN_FUNC, (name,) + tuple(args), offset + token_start))
        return pos

    while pos < len(expr):
        if expr[pos].isspace():
            if token_start != None:
                last = add_value()
                token_start = None
            pos += 1

        elif expr[pos] == '-' and token_start == None and \
                expr[pos+1:pos+2] in string.digits and not last & TOKEN_VALUE:
            token_start = pos
            pos += 1

        elif expr[pos] in '+-' and token_start != None and \
            expr[pos-1:pos] == 'e' and expr[pos-2:pos-1] in string.digits + '.':
            pos += 1

        elif expr[pos:pos+2] in OPS_RTL:
            if token_start != None:
                last = add_value()
                token_start = None

            if last & ~(TOKEN_OP_LTR | TOKEN_LPAREN):
                raise ParseError(offset + pos, 'operator expected')

            tokens.append((TOKEN_OP_RTL, expr[pos:pos+2], offset + pos))
            last = TOKEN_OP_RTL
            pos += 2

        elif expr[pos:pos+2] in OPS_LTR:
            if token_start != None:
                last = add_value()
                token_start = None

            if not last & TOKEN_VALUE:
                raise ParseError(offset + pos, 'value expected1')

            tokens.append((TOKEN_OP_LTR, expr[pos:pos+2], offset + pos))
            last = TOKEN_OP_LTR
            pos += 2

        elif expr[pos] in OPS_RTL:
            if token_start != None:
                last = add_value()
                token_start = None

            if last & ~(TOKEN_OP_LTR | TOKEN_LPAREN):
                raise ParseError(offset + pos, 'operator expected')

            tokens.append((TOKEN_OP_RTL, expr[pos], offset + pos))
            last = TOKEN_OP_RTL
            pos += 1

        elif expr[pos] in OPS_LTR:
            if token_start != None:
                last = add_value()
                token_start = None

            if not last & TOKEN_VALUE:
                raise ParseError(offset + pos, 'value expected2')

            tokens.append((TOKEN_OP_LTR, expr[pos], offset + pos))
            last = TOKEN_OP_LTR
            pos += 1

        elif expr[pos] == '(':
            if token_start == None:
                paren += 1

                if last & ~TOKEN_OPERATOR:
                    raise ParseError(offset + pos, 'operator expected')

                tokens.append((TOKEN_LPAREN, '(', offset + pos))
                last = TOKEN_LPAREN
                pos += 1

            else:
                pos = add_func(pos)
                token_start = None
                last = TOKEN_FUNC

        elif expr[pos] == ')':
            if token_start != None:
                last = add_value()
                token_start = None

            paren -= 1
            if paren < 0:
                raise ParseError(tokens[-1][2], 'unexpected parenthesis')

            if last & TOKEN_OPERATOR:
                raise ParseError(offset + pos, 'value expected')

            tokens.append((TOKEN_RPAREN, ')', offset + pos))
            last = TOKEN_RPAREN
            pos += 1

        else:
            if expr[pos] not in string.digits + string.letters + '._':
                raise ParseError(offset + pos, 'invalid token')

            if token_start == None:
                token_start = pos
            pos += 1

    if token_start != None:
        last = add_value()

    if not tokens or (last & TOKEN_OPERATOR):
        raise ParseError(offset + pos - 1, 'value expected!')

    if paren > 0:
        raise ParseError(offset + pos, 'closing parenthesis expected')

    return tuple(tokens)


def coherse(arg):
    """Wraps a value with a function that converts strings to integers."""

    def inner(env):
        """Converts strings to integers."""

        value = arg(env)
        if isinstance(value, str):
            value = int(value, 0)
        return value
    return inner


def call_func(name, pos, values, env):
    """Calls a func type at expression compute time."""

    func_dict = env.get('funcs',{}).get(name)
    if func_dict == None:
        raise ComputeError(pos, 'undefined func: ' + name)

    func = func_dict['func']

    if func_dict.get('expr', None):
        names = func_dict.get('args', ())
        nreq, narg = len(names), len(values)
        if narg != nreq:
            raise ComputeError(pos, 'func %s expects %d argument(s), got %d' % \
                (name, nreq, narg))

        args = []
        for value in values:
            args.append(value(env))

        stack = env.setdefault('stack', [])
        if name in stack:
            raise ComputeError(pos, 'recursion detected while calling func: ' + \
                name)
        stack.append(name)

        new_env = env.copy()
        new_env['locals'] = dict(zip(names, args))

        try:
            value = func(new_env)
        except ExpressionError as exc:
            stack.pop()
            exc_handler = env.get('exc_handler')
            if exc_handler:
                exc_handler(name, args, exc, env, func_dict.get('expr'))
            raise ComputeError(pos, 'exception in func: ' + name)

        stack.pop()

    else:
        narg, nreq = len(values), func_dict.get('nreq')
        if isinstance(nreq, tuple):
            nreq_min, nreq_max = nreq
            if narg < nreq_min or narg > nreq_max:
                raise ComputeError(pos, 'func %s expects %d to %d arguments, ' \
                    'got %d' % (name, nreq_min, nreq_max, narg))
        else:
            if nreq == None:
                if inspect.isbuiltin(func) or isinstance(func, type):
                    raise ComputeError(pos, 'func %s must have nreq ' \
                        'or nreq_min/nreq_max defined' % name)

                nreq = func.func_code.co_argcount
                if inspect.ismethod(func):
                    nreq -= 1

            if narg != nreq:
                raise ComputeError(pos, 'func %s expects %d argument(s), got ' \
                    '%d' % (name, nreq, narg))

        args = []
        for value in values:
            args.append(coherse(value)(env))

        try:
            value = func(*args)
        except ExpressionError as exc:
            exc_handler = env.get('exc_handler')
            if exc_handler:
                exc_handler(name, args, exc, env, func_dict.get('expr'))
            raise ComputeError(pos, 'exception in func: ' + name)

    return value


def compile_expr(tokens):
    """Compiles an expression in parsed/token form to a tree of lambdas."""

    output = []
    stack = []

    def operator(token):
        """Emits an operator lambda."""

        _, value, _ = token
        func = OPS[value][1]
        args = []
        for _ in xrange(func.func_code.co_argcount):
            args.insert(0, coherse(output.pop()))

        return func(*args)

    def operand(token):
        """Emits an operand lambda."""

        type_, value, pos = token
        if type_ == TOKEN_NUM:
            return lambda env: value

        elif type_ == TOKEN_VAR:
            name = value
            def get_var(env):
                """Compute-time function to resolve a var."""

                value = env.get('locals', {}).get(name)
                if value == None:
                    value = env.get('globals', {}).get(name)
                if value == None:
                    raise ComputeError(pos, 'undefined var: ' + name)

                return value
            return get_var

        elif type_ == TOKEN_FUNC:
            name, token_sets = value[0], value[1:]
            compiled_args = []
            for tokens in token_sets:
                compiled_args.append(compile_expr(tokens))

            return lambda env: call_func(name, pos, compiled_args, env)

        else:
            raise CompileError(pos, 'unsupported token')

    for token in tokens:
        type_, value, _ = token
        if type_ == TOKEN_OP_RTL:
            while stack and stack[-1][0] != TOKEN_LPAREN:
                if OPS[stack[-1][1]][0] <= OPS_RTL[value][0]:
                    break
                output.append(operator(stack.pop()))
            stack.append(token)

        elif type_ == TOKEN_OP_LTR:
            while stack and stack[-1][0] != TOKEN_LPAREN:
                if OPS[stack[-1][1]][0] < OPS_LTR[value][0]:
                    break
                output.append(operator(stack.pop()))
            stack.append(token)

        elif type_ == TOKEN_LPAREN:
            stack.append(token)

        elif type_ == TOKEN_RPAREN:
            while stack and stack[-1][0] != TOKEN_LPAREN:
                output.append(operator(stack.pop()))
            stack.pop()

        else:
            output.append(operand(token))

    while stack:
        output.append(operator(stack.pop()))

    if stack or len(output) != 1:
        raise CompileError(0, 'invalid token input')

    return output[0]


def define_func(env, name, args, expr, desc=None):
    """Compiles an expression and saves it as a function in the environment."""

    if not issymbol(name):
        raise DeclarationError('name is not a valid symbol: ' + name)

    funcs = env.setdefault('funcs', {})

    args = args.strip()
    if args:
        args = tuple(map(str.strip, args.split(',')))
        for arg, count in collections.Counter(args).items():
            if not issymbol(arg):
                raise DeclarationError('arg is not a valid symbol: ' + arg)
            if count > 1:
                raise DeclarationError('arg is specified multiple times: ' + arg)
    else:
        args = ()

    tokens = parse_expr(expr)
    compiled = compile_expr(tokens)
    func = {'expr': expr, 'args': args, 'func': compiled}
    if desc != None:
        func['desc'] = desc
    funcs[name] = func


def undefine_func(env, name):
    if not issymbol(name):
        raise DeclarationError('name is not a valid symbol: ' + name)

    funcs = env.setdefault('funcs', {})
    if funcs.has_key(name):
        del funcs[name]


def define_var(env, name, expr):
    """Compiles and computes an expression, storing the value in the environment."""

    if not issymbol(name):
        raise DeclarationError('name is not a valid symbol: ' + name)

    globals_ = env.setdefault('globals', {})

    tokens = parse_expr(expr)
    compiled = compile_expr(tokens)
    globals_[name] = compiled(env)


def undefine_var(env, name):
    """Undefines a global var."""

    if not issymbol(name):
        raise DeclarationError('name is not a valid symbol: ' + name)

    globals_ = env.setdefault('globals', {})
    if globals_.has_key(name):
        del globals_[name]


def expr_exc_handler(name, args, exc, env, expr):
    """Sample expr exception handler."""

    print 'Error: ' + exc.message
    if expr:
        print '  ' + expr
        print ' ' * (exc.pos + 2) + '^'


if __name__ == '__main__':
    import sys

    env = {}
    env['exc_handler'] = expr_exc_handler
    env['globals'] = BUILTIN_VARS.copy()
    env['funcs'] = BUILTIN_FUNCS.copy()

    define_func(env, 'f0(x)', 'x+1')
    define_func(env, 'f1()', 'x+1')
    define_func(env, 'f2(x)', 'f1()+x')
    define_func(env, 'area_of_circle(r)', '2*pi*r**2')
    define_func(env, 'recurse()', 'recurse()')

    expr = sys.argv[1]

    try:
        tokens = parse_expr(expr)
        compiled = compile_expr(tokens)
        for i in xrange(5):
            env['globals']['x'] = i
            result = compiled(env)
            print 'for x = %d:' % i, expr, '=', result
    except ExpressionError as exc:
        expr_exc_handler('', [], exc, env, expr)
        sys.exit(1)

