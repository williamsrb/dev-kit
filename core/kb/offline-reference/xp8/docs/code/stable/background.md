<!-- src:https://developer.enonic.com/docs/code/stable/background generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/background.md

# Background

Server-side work that doesn’t run in response to an incoming HTTP request — fire-and-forget jobs and scheduled cron-like execution.

## Tasks vs scheduled jobs

XP offers two primitives for background execution. Pick by trigger and timing:

| Primitive | Triggered by | Use when |
| --- | --- | --- |
| [Tasks](docs/code/stable/background/tasks.md) | An explicit `submit()` call | You need to run work asynchronously from a request — long imports, image processing, batch jobs — without blocking the caller. Each task runs once. |
| [Scheduler](docs/code/stable/background/scheduler.md) | A cron expression or one-shot timestamp | You need recurring jobs (nightly reindex, hourly cache warm) or future-dated execution. The scheduler runs your task on the matching schedule. |

Tasks and scheduled jobs share the same execution shape — both invoke a **named task** implementation. The scheduler is the trigger; tasks are the unit of work.

For pub/sub on the cluster-wide bus, see [Events](docs/code/stable/fundamentals/events.md).

## Cluster behavior

Both primitives are cluster-aware:

- **Tasks** run on the node that called `submit()`, unless explicitly distributed.

- **Scheduled jobs** execute on exactly one node per fire. The scheduler coordinates so the same job doesn’t run twice.

See each page for the details.

## Pages in this section

Tasks

Inline and named tasks, the task descriptor, progress reporting, and the task lifecycle.

Scheduler

Cron and one-time scheduled jobs, descriptor format, and how scheduled execution interacts with the task system.
