# -*- coding: utf-8 -*-
# vim: set ts=4 et

from collections import OrderedDict

from .yaml import yaml


config = OrderedDict()

def load(core):
    global config

    with open(core.config_path) as f:
        config = yaml.load(f)


def autoload_list(bot):
    global config

    plugins = ['base']
    for name, options in config[bot.network].get('plugins',
            OrderedDict()).items():
        if name not in plugins and \
                (not options or options.get('autoload', True)):
            plugins.append(name)
    return plugins


def plugin_options(bot, plugin):
    global config

    plugin = config[bot.network].get('plugins', OrderedDict()).get(plugin)
    if plugin:
        return plugin
    return OrderedDict()
