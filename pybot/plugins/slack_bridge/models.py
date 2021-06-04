# -*- coding: utf-8 -*-
# vim: set ts=4 et

from datetime import datetime
import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


__all__ = ['Bridge', 'User']
Base = declarative_base()

class Bridge(Base):
    __tablename__ = 'bridges'
    id = Column(Integer, primary_key=True)
    irc_channel = Column(String, nullable=False)
    slack_channel = Column(String, nullable=False)


    def __init__(self, irc_channel, slack_channel):
        self.irc_channel = irc_channel
        self.slack_channel = slack_channel


    def __repr__(self):
        return '<Bridge(%r)>' % (self.id)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    irc_name = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    slack_name = Column(String, nullable=True, unique=True)


    def __init__(self, irc_name, email, slack_name):
        self.irc_name = irc_name
        self.email = email
        self.slack_name = slack_name


    def __repr__(self):
        return '<User(email=%r)>' % (self.email,)


def init(bot):
    engine = create_engine('sqlite:///' + os.path.join(bot.core.data_path,
            'slack_bridge.' + bot.network + '.db?check_same_thread=false'))
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
