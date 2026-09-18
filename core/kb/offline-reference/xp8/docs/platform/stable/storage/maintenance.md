<!-- src:https://developer.enonic.com/docs/platform/stable/storage/maintenance generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/storage/maintenance.md

# Maintenance

Routine operational tasks for keeping the data store healthy over time.

## Overview

The data store generally runs without manual upkeep, but two operations may be required over the lifetime of an XP instance:

- [**Vacuuming**](#vacuum) — permanently delete blobs and metadata that are no longer referenced.

- [**Reindexing**](#reindex) — rebuild the search index from the blobstore and metadata.

Both can be triggered via the [management endpoints](docs/platform/stable/endpoints/management.md), the [Enonic CLI](https://developer.enonic.com/docs/enonic-cli), or admin applications such as [Data Toolbox](https://market.enonic.com/vendors/glenn-ricaud/data-toolbox).

## Vacuuming

Deleted nodes do not immediately free up storage in XP. Blobs and parts of the version metadata are retained so that previous [snapshots](docs/platform/stable/deployment/backup-restore.md#snapshot-restore) remain restorable. Vacuuming is the controlled mechanism for permanently removing this unreferenced data.

### Vacuum tasks

XP exposes the following vacuum tasks:

| Task | Description |
| --- | --- |
| `VersionTableVacuumTask` | Deletes node metadata that is no longer referenced. *Default.* |
| `SnapshotsVacuumTask` | Deletes snapshots older than the configured age threshold. |
| `SegmentVacuumTask` | Deletes all blobs related to previously deleted repositories. |
| `BinaryBlobVacuumTask` | Deletes binary data blobs that are no longer referenced. |
| `NodeBlobVacuumTask` | Deletes node data blobs that are no longer referenced. |

If no tasks are specified, only the default task (`VersionTableVacuumTask`) runs.

> **Important:** `SegmentVacuumTask`, `BinaryBlobVacuumTask` and `NodeBlobVacuumTask` delete blobs. Because these blobs may still be referenced by older snapshots, **all existing snapshots are automatically deleted** when any of these tasks runs — this prevents XP startup failures that would otherwise occur if an old snapshot were restored against a vacuumed blobstore.

Before running blob-deleting vacuum tasks:

Back up the [blobstore folder](docs/platform/stable/config/system.md#file-blobstore).

Plan to take a fresh [snapshot](docs/platform/stable/deployment/backup-restore.md#snapshot-restore) immediately after the vacuum completes.

> **Tip:** Vacuuming can be scheduled to run automatically, or triggered manually via the CLI.

## Reindexing

The search index can be rebuilt at any time from the authoritative data in the blobstore and metadata index. This is most commonly required after major upgrades, but is also useful when:

- The search index has become corrupted or inconsistent.

- Index configuration has changed on existing content and the new mappings need to be applied.

- You are recovering an instance where the search index is missing or unusable but the blobstore and metadata index are intact.

> **Note:** Reindexing only rebuilds the **search index**. The metadata index is not rebuilt. If the metadata index is lost, recovery must go through [snapshot restore](docs/platform/stable/deployment/backup-restore.md#snapshot-restore).

### Scope

A reindex targets a specific repository and one or more [branches](docs/platform/stable/storage/repositories.md#branches). Reindexing one branch does not affect indices on other branches or other repositories.

When the `initialize` flag is set, the existing search indices are deleted before being rebuilt — this guarantees that all index mappings come from the current state of XP and the installed applications. Without it, the reindex updates the existing indices in place.

### How to trigger

Reindexing can be triggered via:

- The [management endpoint](docs/platform/stable/endpoints/management.md#reindex) — `POST repo/index/reindex` for synchronous runs, or `POST repo/index/reindexTask` for the long-running task variant.

- The [Enonic CLI](https://developer.enonic.com/docs/enonic-cli).

- Admin applications such as [Data Toolbox](https://market.enonic.com/vendors/glenn-ricaud/data-toolbox).

> **Tip:** For large repositories, prefer the task variant and schedule the operation during a maintenance window.
