<!-- src:https://developer.enonic.com/docs/platform/stable/storage generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/storage.md

# NoSQL Data Store

Enonic XP ships with a unique and powerful document-oriented data storage.

## Background

When designing XP, we carefully evaluated existing and popular technologies from Git, file systems, object storage, SQL, the JCR (Java Content Repository), and various other search and NoSQL solutions.

However, we were unable to find any single solution that supported our requirements to functionality, performance, simplicity and technology. So, we decided to build our own NoSQL data store, optimized for our use cases and requirements.

The result is now a central component in Enonic XP.

## Features

The XP Data store enables you to persist, index, query and access data of virtually any kind, fast and efficiently. Below is a highlight of the capabilities provided:

- Create multiple [Repositories](docs/platform/stable/storage/repositories.md) within a single XP deployment

- Create schema-less documents aka [Nodes](docs/platform/stable/storage/repositories.md#nodes)

- Built-in support for hierarchical structures

- Nodes contain key-value entries called [properties](docs/platform/stable/storage/repositories.md#nodes)

- Powerful indexing for fast retrieval and search

- JSON based query language, aggregations, and result highlighting

- Versions are created automatically for every update

- Built-in [Access control](docs/platform/stable/storage/permissions.md) down to a single document

- Git inspired [Branches](docs/platform/stable/storage/repositories.md#branches) enable you to stage and promote your data

- Atomic node updates via scripted editors.

> **Tip:** Visit the [developer documentation](docs/code/stable/storage.md) for querying, aggregations, highlighting, editors, and other developer-facing APIs.

## Management

Data persisted in XP can be managed through various applications and interfaces, but common relevant actions are:

- [snapshot and restore](docs/platform/stable/deployment/backup-restore.md#snapshot-restore) to rollback the entire system to a point in time

- [exporting and importing](docs/platform/stable/deployment/backup-restore.md#export-import) nodes and tree structures using a human readable format

- [dumping and loading](docs/platform/stable/deployment/backup-restore.md#dump-load) your entire storage.

- [backing up](docs/platform/stable/deployment/backup-restore.md#backup) your data safely.

- [maintenance](docs/platform/stable/storage/maintenance.md) — vacuuming unreferenced data and reindexing the search index.
