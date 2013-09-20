# -*- coding: utf-8 -*-
# vim: set ts=4 et

import random

from plugin import *


class Plugin(BasePlugin):
    @trigger_hook
    def choose(self, msg, args, argstr):
        argstr = argstr.replace(' or ', ',').replace(',or ', ',')
        choices = [x for x in map(str.strip, argstr.split(',')) if x]
        if not choices:
            responses = [
                "Choices choices.. which do I choose from.  Oh right, I don't.",
                "You've got to give me something to work with here!",
                "...",
                "You're supposed to be asking me the questions.  What exactly is your plan?",
                "Look {0}, you've got to give me some options.",
                "No choices?  Empty result set.",
                "\x01ACTION looks at {0} and just walks away.  Slowly.\x01",
            ]
        elif len(choices) == 1:
            responses = [
                "You've forced me to go with {1}.",
                "{1}.  Is there anything else I can help you with, {0}?",
                "I'm not playing this game, {0}.",
                "If you go with {1}, I'm leaving.",
                "{0}, you displease me.",
                "No.",
                "Why would you ask me to choose one thing? WHY?!",
            ]
        else:
            responses = [
                "I suggest you choose {1}.",
                "I'd go with {1}.",
                "Perhaps {1} is the right choice.",
                "Well, I wouldn't go with {1}.",
                "Are you sure you want to go with {1}?",
                "I like {1}.",
                "{1}. Definately {1}.",
            ]

        response = random.choice(responses)
        choice = random.choice(choices) if choices else None
        msg.reply(response.format(msg.nick, choice))

