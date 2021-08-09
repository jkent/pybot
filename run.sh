#!/bin/sh

if [ ! -d venv ]; then
    python3 -m virtualenv venv
fi

. venv/bin/activate
python3 -m pip install -r requirements.txt

exec python3 pybot.py
