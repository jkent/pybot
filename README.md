jkent-pybot
===========

This is a modular, plugin-based IRC bot written in Python.  Plugins can be dynamically loaded and unloaded at runtime.  A design goal is the abillity to develop plugins without being able to crash the bot.

Plugins have a simple, easy to pick up API.  All events, commands, and triggers use a simple decorator convention.

Checkout with:  ```git clone --recursive https://github.com/jkent/jkent-pybot.git```

### Plugins
Here's a simple "Hello world" style plugin:

    import * from plugin
    
    class Plugin(BasePlugin):
        @hook
        def hello_trigger(self, msg, args, argstr):
            msg.reply('Hello %s!' % argstr)

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

