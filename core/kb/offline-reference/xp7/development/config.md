<!-- src:https://developer.enonic.com/docs/platform/7.x/development/config generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC development/config.md

# Application config

Applications may be configured via file.

## Config folder

Your development environment (aka sandbox), can read application-specific configurations files and provision this to each app. By default, it will scan the folder located in `$XP_HOME/config/`

> **Note:** The config folder also contains the [standard XP configuration files](/docs/platform/7.x/deployment/config).

## Config file

Simply adding or updating a file called `.cfg` in the config folder will automatically restart your application, and provision the new configuration values.

This is a hot restart, and will typically be very fast. XP itself does not need to be restarted.

> **Note:** If you’re operating an XP cluster, the configuration file should be copied to every server node - this is because XP by default will run all applications on every node in the cluster.

## Accessing config

Developers can easily access the application’s config via the JavaScript controllers.

Given the following configuration file:

.cfg

```properties
secretkey = 123456789
```

The value can be optained using a single line of code:

Sample JS controller

```JavaScript
var myKey = app.config.secretkey;
```
