<!-- src:https://developer.enonic.com/docs/platform/stable/config generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/config.md

# Platform Configuration

This section describes how to configure Enonic XP and installed applications.

## Config folder

The [XP_HOME/config/](docs/platform/stable/deployment/distro.md#xp_home) folder contains all of your configuration files. It’s actual location will depend on your deployment.

## License folder

Some applications may require a license in order to work properly. The `XP_HOME/license` folder is where the system looks for licenses. The license should be named `.lic`. If you are running an app with a license, please ask the supplier for the app license file.

Enonic apps like Content Studio+, Live Trace and Booster require a license issued by Enonic to work. The app key for XP is "enonic.platform.subscription", so the license should be named `enonic.platform.subscription.lic`.

## File Format

All configuration files (both .cfg and .properties) use the [properties](https://docs.oracle.com/javase/6/docs/api/java/util/Properties.html#load%28java.io.Reader%29) format. This is a simple key = value format.

Sample config file

```properties
mySetting = true
another.setting = Not so sure
multiline.value = another \
                  line
```

## Variables

You may use value variables, as these are often useful to handle dynamic settings.

Sample config with variable

```properties
another.setting = ${myvaraible}
somePath = ${xp.home}/myfolder
```

## Hot deployment

When changing files ending with `.cfg`, application using them will automatically restart with the new configuration loaded. Files ending with `.properties` require a full restart of the XP instance to be effectively applied.

## Clustered deployments

In a clustered environment, configuration files must be distributed to all nodes where it is relevant. This also means you may have different configuration files on different nodes - but be careful as some configuration files may cause issues if they are not consistent across the cluster.
