# -*- coding: utf-8 -*-
# vim: set ts=4 et

from .multidict import MultiDict
from .yaml import yaml


config = MultiDict()

def load(core):
    global config

    with open(core.config_path) as f:
        config = yaml.load(f)
