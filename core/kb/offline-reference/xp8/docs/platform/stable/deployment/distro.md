<!-- src:https://developer.enonic.com/docs/platform/stable/deployment/distro generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/deployment/distro.md

# XP distributions

This chapter investigates the anatomy of the XP distribution filestructure

## Introduction

XP is built and distributed as a self-contained package for multiple different architectures, which includes all necessary components to run the platform. This includes the application code, embedded GraalVM, configuration files, and more.

## Downloading

Pre-compiled XP distributions can be manually downloaded from the [Enonic Repo](https://repo.enonic.com/#browse/browse:public:com), or built from source on [GitHub](https://github.com/enonic/xp).

Also check out the [docker.ahtml](docs/platform/stable/deployment/docker.md) versions of XP, which are based on the same distributions, but optimized for containerized deployment.

## Server vs SDK

Enonic XP is available in two different packages: Server and SDK.

The Server version is secured by default and optimized for production use, while the SDK version is intended for development and testing purposes.

The SDK version includes additional tools and libraries that are not necessary for running XP in a production environment.

For development on the XP platform, check out the [Enonic Developer Docs](https://developer.enonic.com/docs/code).

## XP_INSTALL

When downloading and unzipping the XP distro, you will find the following root structure inside:

XP distribution folder structure

```folders
enonic-xp-<OS>-<type>-<version>  (1)
 |- bin/  (2)
 |- home/   (3)
 |- java/  (4)
 |- lib/  (5)
 |- service/  (6)
 |- system/  (7)
```

| ****1** | The root folder is simply referred to as XP_INSTALL. |
| --- | --- |
| ****2** | `bin/*` contains the scripts for starting and stopping Enonic XP and setting environment variables. |
| ****3** | `home/` also known as [XP_HOME](#xp_home) |
| ****4** | `java/` contains the embedded JVM distro, contents vary with distro |
| ****5** | `lib/` contains the bootstrap code used to launch Enonic XP. |
| ****6** | `service/` contains install script for Linux to make Enonic XP run as a service |
| ****7** | `system/` Default OSGi bundles are placed here. |

## XP_HOME

Inside the XP_INSTALL folder, you will find the `home/` folder, which is also referred to as XP_HOME. This is the default location for all data and configuration files used by Enonic XP.

It is commonly moved out or treated specially from the rest of the files and folders in XP_INSTALL, as it contains stateful data. An example of this is when using Enonic CLI. Each "sandbox" created is basically a copy of the XP_HOME structure.

You may override the default location of XP_HOME by passing a boot parameter to XP, or by creating an XP_HOME environment variable.

> **Note:** Folders marked with * will not appear until XP is started the first time

Standard folder structure

```folders
XP_HOME/
|- config/  (1)
|- data/ *  (2)
   |- dump/
   |- export/
|- deploy/  (3)
|- logs/  (4)
|- repo/ *
   |- index/  (5)
   |- blob/  (6)
|- snapshots/ *  (7)
|- work/   (8)
```

| ****1** | `config/` holds all configuration files, including vhost.cfg and system.properties. XP supports hot reloading of all files ending with .cfg |
| --- | --- |
| ****2** | `data/` Contains system dumps and exports.   @@BLOCK1@@ |
| ****3** | `deploy/` Apps placed here are automatically loaded and started on the specific node. |
| ****4** | `logs/` default output location for all logs. |
| ****5** | `repo/index/` contains repository metadata and indexes   @@BLOCK2@@ |
| ****6** | `repo/blob/` contains the XP blobstore   @@BLOCK3@@ |
| ****7** | `snapshots/` Location where snapshots (of index and metadata) are stored when using the snapshot-operation.   @@BLOCK4@@ |
| ****8** | `work/` Cache and generated bundles (apps etc) are stored here. It is also a default location for temporary files.   @@BLOCK5@@     == XP_TMP |

By default, Enonic XP uses `XP_HOME/work` as temporary folder.

You may override this by setting the `XP_TMP` environment variable to point to a different location.
