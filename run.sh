#!/bin/sh

if [ ! -d venv ]; then
    virtualenv venv
fi

. venv/bin/activate
pip install -r requirements.txt

exec python pybot.py
