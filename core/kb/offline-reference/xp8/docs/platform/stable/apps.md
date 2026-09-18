<!-- src:https://developer.enonic.com/docs/platform/stable/apps generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/apps.md

# Enonic Applications

Build and deploy schemas, code, and functionality via Enonic applications.

## Introduction

Enonic applications are standalone software packages that can be installed and started on Enonic XP. The App runtime can run multiple applications in a single instance simultaneously.

Once started, an application has access to all platform services, including the [NoSQL storage](docs/platform/stable/storage.md) and [identity and access management](docs/platform/stable/security.md).

A single application may offer many different capabilities, from CMS schemas to exposing APIs to other apps. Fundamentally, most of XP’s core software components are built as applications.

## Enonic Market

[Enonic market](https://market.enonic.com) is the go-to place for official apps from Enonic, as well as 3rd party applications. The marketplace also offers starter kits and software libraries that help you create new apps better and faster.

## Installation

There are four ways to get your applications running on Enonic XP:

Via Admin Interface

Applications can be manually installed through the [Applications admin tool](docs/platform/stable/admin/applications.md), included with Enonic XP. Once installed, the applications will be available for all nodes in an XP cluster.

Via Management API

Applications can be installed through the Management API. The applications will be available for all nodes in an XP cluster. This approach is commonly used in a CI/CD setup.

Via File system

File system deployment is most commonly used during development, but it can also be applied for specialized deployment scenarios. Applications deployed on file will only be available on the local node, and overrides applications installed via other alternatives.

Microservice bundle

Consider a microservice style highly controlled setup where you bundle your app(s) together with the XP runtime and launch it as a separate instance.

## Life cycle

In addition to installing and uninstalling, Enonic applications may be started and stopped. This is referred to as the life cycle of the application. During the stop and start phases, applications themselves may execute custom code.

Starting

Once installed, applications are automatically started on all nodes. During startup, if it exists, the application’s `main.js` script will be executed.

Stopping

Before uninstalling, applications are automatically stopped on all nodes. During stopping, if it exists, the disposer of the application’s `main.js` script will be executed.

## Configuration

Applications can be configured by adding a [custom configuration file](docs/platform/stable/config/system.md) `.cfg` (i.e. `my.custom.app.cfg`) to your Enonic instance.

## Building applications

For details on building applications — including the App runtime, JavaScript framework, and engines for sites, webapps, tasks, and admin tools — see the [Enonic Development Kit](https://developer.enonic.com/docs/code).
