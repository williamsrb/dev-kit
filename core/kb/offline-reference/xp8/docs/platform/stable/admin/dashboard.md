<!-- src:https://developer.enonic.com/docs/platform/stable/admin/dashboard generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/admin/dashboard.md

# Dashboard

The Dashboard is the default landing tool of the XP admin, providing a customizable overview of your instance.

## Introduction

The Dashboard is opened automatically the first time you sign in, and acts as a home screen for the admin. It is composed entirely of widgets, arranged in a configurable grid.

Out of the box, the Dashboard shows a small set of built-in widgets. Installing applications such as Content Studio will contribute additional widgets, such as a list of recently edited content.

## Default widgets

Useful Links

A curated list of links to documentation, the Enonic Market, and other resources to help you get started.

Statistics

Surfaces basic runtime information about the XP instance, including version and node details. Backed by the [Statistics API](docs/platform/stable/endpoints/statistics.md).

> **Note:** The Dashboard reflects what is installed and which roles your user has - widgets defined by an application only appear once the app is installed and started, and only for users with sufficient privileges.

## Customizing the dashboard

The Dashboard is fully extensible. Any application may contribute new widgets by providing extensions that implementing the `admin.dashboard` interface, controlling their priority, size, and styling.

For details on building and configuring Dashboard widgets, see [Code examples](docs/code/stable/examples.md).
