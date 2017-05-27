# -*- coding: utf-8 -*-
# vim: set ts=4 et

from plugin import *
import expression
import os
import re
import sqlite3


VAR_TYPE_INT     = 0
VAR_TYPE_FLOAT   = 1
VAR_TYPE_COMPLEX = 2
VAR_TYPE_STR     = 3


class Plugin(BasePlugin):
    def on_load(self, reloading):
        self.db = sqlite3.connect(os.path.join(self.bot.core.data_path, 'math.db'))
        c = self.db.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS Workbook (
              WorkbookId INTEGER      PRIMARY KEY AUTOINCREMENT NOT NULL,
              Name       VARCHAR(100) NOT NULL
            );''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS Funcs (
              WorkbookId INTEGER      NOT NULL REFERENCES Workbook(WorkbookId),
              Name       VARCHAR(100) NOT NULL,
              Args       VARCHAR(100) NOT NULL,
              Expr       VARCHAR(100) NOT NULL,
              Desc       VARCHAR(100)
            );''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS Vars (
              WorkbookId INTEGER      NOT NULL REFERENCES Workbook(WorkbookId),
              Name       VARCHAR(100) NOT NULL,
              Type       INTEGER      NOT NULL,
              Value      VARCHAR(100) NOT NULL
            );''')
        self.db.commit()

        self.workbooks = {}
        self.target_to_workbook = {}

    def on_unload(self, reloading):
        self.db.close()

    def load_workbook(self, target, name):
        if ':' not in name:
            name = target + ':' + name

        if name in self.workbooks:
            self.target_to_workbook[target] = self.workbooks[name]
            return self.target_to_workbook[target]

        self.target_to_workbook[target] = self.workbooks[name] = workbook = {}
        workbook['name'] = name
        workbook['exc_handler'] = self.exc_handler
        workbook['globals'] = expression.BUILTIN_VARS.copy()
        workbook['funcs'] = expression.BUILTIN_FUNCS.copy()

        c = self.db.cursor()
        c.execute('SELECT WorkbookId FROM Workbook WHERE Name=:name', workbook)
        row = c.fetchone()
        if not row:
            c.execute('INSERT INTO Workbook (Name) ' \
                'VALUES (:name)', workbook)
            self.db.commit()
            workbook['id'] = c.lastrowid
            return workbook

        workbook['id'] = row[0]

        c.execute('SELECT Name, Type, Value FROM Vars WHERE WorkbookId=:id', workbook)
        for row in c.fetchall():
            name, type_, value = row
            if type_ == VAR_TYPE_INT:
                value = int(value)
            elif type_ == VAR_TYPE_FLOAT:
                value = float(value)
            elif type_ == VAR_TYPE_COMPLEX:
                value = complex(value)
            else:
                value = str(value)
            workbook['globals'][str(name)] = value

        c.execute('SELECT Name, Args, Expr, Desc FROM Funcs WHERE WorkbookId=:id', workbook)
        for row in c.fetchall():
            name, args, expr, desc = str(row[0]), str(row[1]), str(row[2]), str(row[3])
            expression.define_func(workbook, name, args, expr, desc)

        return workbook

    def get_workbook(self, target):
        if target in self.target_to_workbook:
            return self.target_to_workbook[target]

        return self.load_workbook(target, 'Default')

    def exc_handler(self, name, args, exc, workbook, expr):
        self.lastmsg.reply('Error: ' + exc.message)
        if expr:
            self.lastmsg.reply('  ' + expr)
            self.lastmsg.reply(' ' * (exc.pos + 2) + '^')

    def define_func(self, msg, workbook, name, args, expr):
        try:
            expression.define_func(workbook, name, args, expr)
            c = self.db.cursor()
            c.execute('INSERT INTO Funcs VALUES (?, ?, ?, ?, ?)', \
                (workbook['id'], name, args, expr, ''))
            self.db.commit()
        except expression.DeclarationError as exc:
            msg.reply('Error: ' + exc.message)
        except expression.ExpressionError as exc:
            self.exc_handler('', [], exc, workbook, expr)

    def undefine_func(self, msg, workbook, name):
        try:
            expression.undefine_func(workbook, name)
            c = self.db.cursor()
            c.execute('DELETE FROM Funcs WHERE WorkbookId=? and Name=?', \
                (workbook['id'], name))
            self.db.commit()
        except expression.DeclarationError as exc:
            msg.reply('Error: ' + exc.message)

    def define_var(self, msg, workbook, name, expr):
        try:
            expression.define_var(workbook, name, expr)

            value = workbook['globals'][name]
            if type(value) in [int, int]:
                type_ = VAR_TYPE_INT
            elif type(value) == float:
                type_ = VAR_TYPE_FLOAT
            elif type(value) == complex:
                type_ = VAR_TYPE_COMPLEX
            else:
                type_ = VAR_TYPE_STR

            c = self.db.cursor()
            c.execute('INSERT INTO Vars VALUES (?, ?, ?, ?)', (workbook['id'], \
                name, type_, str(value)))
            self.db.commit()
        except expression.DeclarationError as exc:
            msg.reply('Error: ' + exc.message)
        except expression.ExpressionError as exc:
            self.exc_handler('', [], exc, workbook, expr)

    def undefine_var(self, msg, workbook, name):
        try:
            expression.undefine_var(workbook, name)
            c = self.db.cursor()
            c.execute('DELETE FROM Vars WHERE WorkbookId=? and Name=?', \
                (workbook['id'], name))
            self.db.commit()
        except expression.DeclarationError as exc:
            msg.reply('Error: ' + exc.message)

    @hook
    def math_trigger(self, msg, args, argstr):
        self.lastmsg = msg
        workbook = self.get_workbook(msg.reply_to)

        line = str(argstr).strip()

        m = re.match('(\w+)\(([\w, ]*)\)\s*=\s*(.*)', line)
        if m:
            name, args, expr = m.groups()
            expr = expr.strip()
            self.undefine_func(msg, workbook, name)
            if expr:
                self.define_func(msg, workbook, name, args, expr)
            return

        m = re.match('(\w+)\s*=\s*(.*)', line)
        if m:
            name, expr = m.groups()
            expr = expr.strip()
            self.undefine_var(msg, workbook, name)
            if expr:
                self.define_var(msg, workbook, name, expr)
            return

        try:
            expr = line
            tokens = expression.parse_expr(expr)
            compiled = expression.compile_expr(tokens)
            value = compiled(workbook)
        except expression.ExpressionError as exc:
            self.exc_handler('', [], exc, workbook, expr)
            return
        except Exception as exc:
            msg.reply('Error: ' + exc.message)
            return
        msg.reply(str(value))

    @hook
    def math_workbook_trigger(self, msg, args, argstr):
        if len(args) <= 1:
            workbook = self.get_workbook(msg.reply_to)
            msg.reply("%s workbook, %d vars, %d funcs" % (workbook['name'], \
                len(workbook['globals']), len(workbook['funcs'])))
            return True

        self.load_workbook(msg.reply_to, args[1])
        return True

    @hook
    def math_varlist_trigger(self, msg, args, argstr):
        workbook = self.get_workbook(msg.reply_to)
        names = list(workbook.get('globals', {}).keys())
        names.sort()
        msg.reply(', '.join(names))
        return True

    @hook
    def math_funclist_trigger(self, msg, args, argstr):
        workbook = self.get_workbook(msg.reply_to)
        names = list(workbook.get('funcs', {}).keys())
        names.sort()
        msg.reply(', '.join(names))
        return True

    @hook
    def math_describe_trigger(self, msg, args, argstr):
        workbook = self.get_workbook(msg.reply_to)
        if len(args) < 2:
            msg.reply('a func name is required')
            return True

        name = args[1]
        funcs = workbook.get('funcs', {})
        if name not in funcs:
            msg.reply(name + ' is not a defined func')
            return True

        func = funcs[name]

        if len(args) < 3:
            if 'expr' in func:
                args = func.get('args', ())
                msg.reply('%s(%s) = %s' % (name, ', '.join(args), func['expr']))
            else:
                msg.reply(name + ' is a python func')

            if 'desc' in func:
                msg.reply(func['desc'])

            return True

        func['desc'] = argstr[len(args[1]):].strip()
        c = self.db.cursor()
        c.execute('UPDATE Funcs SET Desc=? WHERE WorkbookId=? and Name=?', \
            (func['desc'], workbook['id'], name))
        self.db.commit()
        return True
