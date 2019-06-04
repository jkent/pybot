# -*- coding: utf-8 -*-
# vim: set ts=4 et

from datetime import datetime
import os
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


__all__ = ['Message', 'Preference', 'Block']
Base = declarative_base()


class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    nick = Column(String, nullable=False)
    addressee = Column(String, nullable=False)
    next_notify = Column(DateTime, nullable=False)
    channel = Column(String)
    text = Column(String, nullable=False)
    presented = Column(Boolean, nullable=False)

    def __init__(self, nick, addressee, text, channel=None, delta=None):
        self.nick = nick
        self.addressee = addressee
        self.text = text
        self.channel = channel
        self.next_notify = datetime.utcnow()
        if delta:
            self.next_notify += delta
        self.presented = False

    def __repr__(self):
        return '<Message(id=%d)>' % (self.id,)


class Preference(Base):
    __tablename__ = 'preferences'
    nick = Column(String, primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(String)

    def __init__(self, nick, key, value):
        self.nick = nick
        self.key = key
        self.value = value

    def __repr__(self):
        return '<Preference(nick=\'%s\', key=\'%s\'>' % (self.nick, self.key)


class Block(Base):
    __tablename__ = 'block_list'
    nick = Column(String, primary_key=True)
    block = Column(String, primary_key=True)

    def __init__(self, nick, block):
        self.nick = nick
        self.block = block

    def __repr__(self):
        return '<Block(nick=\'%s\', block=\'%s\'>' % (self.nick, self.block)


def init(bot):
    engine = create_engine('sqlite:///' + os.path.join(bot.core.data_path, 'message.db'))
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
