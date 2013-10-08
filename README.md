jkent-pybot
===========

This is a modular, plugin-based IRC bot written in Python.  Plugins can be dynamically loaded and unloaded at runtime.  A design goal is the abillity to develop plugins without being able to crash the bot.

Plugins have a simple, easy to pick up API.  All events, commands, and triggers use a simple decorator convention.


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
There are four types of hooks:

  * event
  * command
  * trigger
  * timestamp

All except for timestamp hooks can be used via the `@hook` decorator.  `@hook` is a smart decorator that uses the naming convention of your method to determine the name and type of the hook.  Alternatively, it can be called as `@hook(names)` and `@hook(type, names)`.

Timestamp hooks can be created 3 different ways: one-shot timeouts, one-shot timers, and repeating intervals.  They are discussed in more detail with the Bot class.

### Bot class
Anything that you may need to access should be accessable from the bot class.  Plugins get a reference to the *bot instance* they are running on (`self.bot`).

var       |description
:---------|:-----------
`channels`|A list of channels currently joined
`core`    |The core instance the bot is running under
`hooks`   |An instance of the Hooks class *(the hook manager)*
`nick`    |A string identifying the bot's current nickname
`plugins` |An instance of the Plugins class *(the plugin manager)*

method                           |description
:--------------------------------|:-----------
`install_hook(owner, hook)`      |Install `hook` for `owner`
`join(channels[, keys])`         |Convenience method for JOIN
`notice(target, text)`           |Convenience method for NOTICE
`part(channels[, message])`      |Convenience method for PART
`privmsg(target, text)`          |Convenience method for PRIVMSG
`set_interval(owner,fn, seconds)`|Install timestamp hook, calls `fn` every `seconds`
`set_timeout(owner, fn, seconds)`|Install timestamp hook, calls `fn` after `seconds`
`set_timer(owner, fn, timestamp)`|Install timestamp hook, calls `fn` at `timestamp`
`uninstall_hook(hook)`           |Uninstall `hook`

### Hook class *(the hook manager)*
You normally do not need to use the hook class directly, unless you want to create new hook types or use hooks dynamically.

method                                      |description
:-------------------------------------------|:----------
`call(hooks, *args)`                        |Call hooks using as many args as possible
`create(fn, type, desc[, priority][, data])`|Add hook of `type` identified by `desc`
`find(type, left[, right])`                 |Search for hooks
`install(hook)`                             |Install `hook`
`modify(hook)`                              |Context manager for modifying *installed* hooks
`uninstall(hook)`                           |Uninstall `hook`
