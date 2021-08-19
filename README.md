pybot
=====

This is a modular, plugin-based IRC bot written in Python.  Plugins can bedynamically loaded and unloaded at runtime.  A design goal is the abillity to develop plugins without being able to crash the bot.

Plugins have a simple, easy to pick up API.  All events, commands, and triggers use a simple decorator convention.

Clone with:  `git clone --recursive https://github.com/jkent/pybot.git`

### Dependencies

Pybot is designed and tested to run under Python 3. Python 2 is no longer supported.  Dependencies are listed in `requirements.txt`.

### Configuring

You need to copy `config.yaml.example` to `config.yaml` and edit it to your liking.

The below examples in the **Plugins** section assume `directed_triggers` is `False`.  Directed triggers start with the bot's name, followed by a colon or comma, and finally the command and any arguments.  The other option, classic triggers, take a ! followed by the command and any arguments.  The default option is to use directed triggers, so multiple bots can peacefully coexist.

  * config.yaml:

        my_network:
          host: localhost
          port: 6667
          ssl: false

          plugins:
            base:
              connect_password: null
              nickname: pybot
              username: pybot
              realname: Python IRC bot - http://git.io/M1XRlw
              nickserv_password: null
              channels:
                  - '#dev'


### Running

Pybot can be run as either a package or using its pybot.py script.  It also comes with a shell script, `run.sh` that will setup a python virtual environment and dependencies for you.

### Plugins

#### anyurl

This plugin will fetch and reply with the og:title or title of a HTML document.

  * Configuration:

        anyurl:
          blacklist:
            - '^https://www.google.com/.*$'


#### base

This plugin handles some of the core behaviors of the bot, such as setting the nick, joining channels, and auto-reconnect.  Its required, please don't unload it unless you know what you're doing.

  * Configuration:

        base:
          nickname: pybot
          channels:
            - #dev
            - #UnderGND


#### choose

A fun yet frustrating plugin that gives random responses.

  * Usage:

        should I|<nick> <question>?
        !choose a or b, c.


#### config

This plugin allows configuration reloading.  Usage is limited to level 1000.

  * Usage:

        !config reload


#### debug

This plugin prints all IRC traffic and module events while loaded.

  * Usage:

        !raw <message>
        !eval <code>

Raw lets you send a raw IRC message, and requires permission level 900 and up. Eval is a dangerous feature that allows arbitrary execution of python code, and usage requires permission level 1000 and up.


#### github

This plugin will show information about GitHub users and repos when a url is linked within a channel.  jrspruitt was the original author, rewritten by jkent.

  * Usage:

        <url>


#### math

The math plugin is a nifty calculator that has support for functions and variables.  Its state is saved in a database as workbooks which can be switched out as needed.

  * Usage:

        !math [expr]
        !math var=[expr]
        !math func([var[, ...]])=[expr]
        !math workbook [name]
        !math varlist
        !math funclist
        !math describe <funcname> [description]


#### message

An offline/delayed message facility.

  * Usage:

        !message send <nick> <message> [as dm] [in timespec]
        !message ack
        !message del <num>
        !message list [nick]
        !message block <nick>
        !message unblock <nick>
        !message opt <in | out>


#### perms

Manage bot permissions.  Usage is limited to level 1000.

  * Config:

        perms:
          superuser: me!root@localhost

  * Usage:

        !perms list
        !perms allow [-]<mask> [<plugin>=<n>]
        !perms deny [-]<mask> [<plugin>=<n>]

Where plugin is the name of a plugin and n is the level to set.  Plugin can be the special constant ANY.


#### plugin

Load, unload, reload plugins at runtime.  Usage is limited to level 1000.

  * Usage:

        !plugin load <name>
        !plugin reload [!]<name>
        !plugin unload [!]<name>
        !plugin list


For reload and unload, the "bang" means force.  Use with caution.


#### song

Choose a random song from a song database.

  * Usage:

        !song
        !song add <artist> - <title>
        !song delete
        !song fix artist <artist>
        !song fix title <title>
        !song last
        !song load <data-file>
        !song search <query>
        !song stats
        !song who
        !song [youtube|yt] <youtube-url>
        !song [youtube|yt] delete


#### topic

Allow users to set the topic with a minimum age.

  * Configuration:

        topic:
          min_age: 24h
          min_level: 100
          bypass_level: 900

  * Usage:

        !topic apply
        !topic set <topic>

If permissions or min_age not met, apply can be used to override and apply the last proposed topic by anyone with bypass_level or higher.


#### twitter

Parse URLs, get latest user tweet, and search keywords on Twitter.
Configuration requires Twitter account and application setup:

  * Configuration:

        twitter:
        apikey: <api key>
        secret: <api secret>
        auth_token: <auth token>
        auth_secret: <auth secret>

  * Usage:

        <url>
        !twitter user <@user_id>
        !twitter search <keyword>


## For Developers

### Plugins
Here's a simple "Hello world" style plugin:

    from pybot.plugin import *

    class Plugin(BasePlugin):
        @hook
        def hello_trigger(self, msg, args, argstr):
            msg.reply('Hello %s!' % (argstr,))

You would call the trigger on IRC via either:

    !hello world

or if directed (conversational) style triggers are enabled:

    pybot, hello world

To which the bot would reply:

    <pybot> Hello world!

### Hooks
There are five types of hooks:

  * event
  * command
  * trigger
  * timestamp
  * url

All except for timestamp hooks can be used via the `@hook` decorator.  `@hook` is a smart decorator that uses the naming convention of your method to determine the name and type of the hook.  Alternatively, it can be called as `@hook(names)` and `@hook(type, names)`.

Timestamp hooks can be created 3 different ways: one-shot timeouts, one-shot timers, and repeating intervals.  They are discussed in more detail with the Bot class.

### Bot class
Anything that you may need to access should be accessable from the bot class.  Plugins get a reference to the *bot instance* they are running on (`self.bot`).

var          |description
:------------|:-----------
`channels`   |A dict with keys being channels, value is a dict with keys 'joined' and 'nicks'
`core`       |The core instance the bot is running under
`hooks`      |An instance of the HookManager class
`nick`       |A string identifying the bot's current nickname
`plugins`    |An instance of the PluginManager class
`allow_rules`|Allow rules for the permission system
`deny_rules` |Deny rules for the permission system

method                              |description
:-----------------------------------|:-----------
`set_interval(fn, seconds[, owner])`|Install timestamp hook, calls `fn` every `seconds`
`set_timeout(fn, seconds[, owner])` |Install timestamp hook, calls `fn` after `seconds`
`set_timer(fn, timestamp[, owner])` |Install timestamp hook, calls `fn` at `timestamp`
`join(channels[, keys])`            |Convenience method for JOIN
`notice(target, text)`              |Convenience method for NOTICE
`part(channels[, message])`         |Convenience method for PART
`privmsg(target, text)`             |Convenience method for PRIVMSG

### Hook class
method             |description
:------------------|:-----------
`bind(fn[, owner])`|Binds a hook in preparation to install

### EventHook class
### CommandHook class
### TriggerHook class
### TimestampHook class
### UrlHook class

### HookManager class *(the hook manager)*
method              |description
:-------------------|:----------
`install(hook)`     |Install a bound `hook`
`uninstall(hook)`   |Uninstall `hook`
`call(hooks, *args)`|Call hooks using as many args as possible
`find(model)`       |Search for hooks by model hook instance
`modify(hook)`      |Context manager for modifying *installed* hooks
