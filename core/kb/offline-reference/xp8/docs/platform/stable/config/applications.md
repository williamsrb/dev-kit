<!-- src:https://developer.enonic.com/docs/platform/stable/config/applications generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/config/applications.md

# Custom' Configuration files

This section describes how custom configuration files work in Enonic XP, and how to use them in your applications.

## Custom config

To provide file based configuration to custom applications, simply place a file with the name `.cfg` i.e. `my.custom.app.cfg`. in the `XP_HOME/config/` folder, and it will instantly be available for the application.

Changing these files while XP is running will restart the application. When the application boots, it will use the new version of the configuration.

This configuration is instantly available for developers via the global `app` object.
