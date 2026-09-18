<!-- src:https://developer.enonic.com/docs/platform/7.x/development/sandboxes generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC development/sandboxes.md

# Sandboxes

Sandboxes are independent Enonic XP development environments

> **Note:** Using CLI, and sandbox may be created and started with the following commands: `enonic sandbox create`, `enonic sandbox start`.

Below, we dive into details of manually setting up and starting sandboxes:

## Download distro

Start by downloading an [Enonic XP distribution file](/docs/platform/7.x/deployment/distro). This is essentially the software version of the Enonic XP platform.

Distros for your architecture can be downloaded from [the Enonic repo](https://repo.enonic.com/service/rest/repository/browse/public/com/enonic/xp/). Look for folders named `enonic-xp--sdk`.

> **Note:** Only distros ending with `sdk` are suitable for development purposes

## Starting sandbox

After downloading and unzipping the distro, Enonic XP can be started on your local machine with the following command:

```
enonic-xp-<architecture>-sdk-<version>/bin/server.sh
```

Where  and  match the distro you downloaded.

## Multiple sandboxes

If you wish to run multiple Sandboxes, this can be done by copying the `home` folder (located within your distro) to a new location. Then, use the `XP_HOME` environment variable to let XP know where to find it.

XP_HOME

Defaults to the `$DISTRO_FOLDER/home/` folder

To set these variables use one of the following approaches:

Linux/MacOS

```
export XP_HOME=/path/to/home
```

Windows

```
set XP_HOME=c:\path\to\home
```
