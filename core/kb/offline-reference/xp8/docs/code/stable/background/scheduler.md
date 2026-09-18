<!-- src:https://developer.enonic.com/docs/code/stable/background/scheduler generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/background/scheduler.md

# Scheduler

Named [tasks](docs/code/stable/background/tasks.md) can be scheduled to asynchronously run in the background in a cluster or a one-node environment.

## Scheduled Job

A scheduled job is an object which describes how a named task must be run. It contains information about the type of scheduling, time of execution, description, etc. All job nodes are stored in a separate `system.scheduler` repository. See how to manipulate it with [lib-scheduler](docs/code/stable/libraries/lib-scheduler.md) API.

Properties

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| name | string | Name of a job, unique for the entire environment |  |  |
| description | string | String-format description of scheduled job |  |  |
| descriptor | string | Descriptor of the task to be scheduled. Format: `<applicationKey>:<taskName>` |  |  |
| config | object | JSON object contains described task parameters |  |  |
| calendar | object | Describes when the task should run      Properties                Name | Type | Description |
| value | string | schedule value according to its type |  |  |
| type | string | schedule type ([CRON](#cron) to be executed repeatedly or [ONE_TIME](#one-time) to be executed once) |  |  |
| timezone | string | time zone of cron scheduling. It doesn’t apply to a onetime calendar. |  |  |

user

string

Principal key of the task submitter. Format: `:`

enabled

boolean

If `true` - the job is active and can be run according to it’s cron value and timezone.

creator

string

Principal key of user that created the task

modifier

string

Principal key of the last user that modified the task

createdTime

string

Time of the task creation

modifiedTime

string

Time of the last task modification

lastRun

string

Time of the last job run

lastTaskId

string

Task id of the last job run

## Calendar

Calendar object describes when and how the task should be run. There are two possible types: one-time and cron.

one-time

The task will be run only once. If the time value is passed at the moment of scheduling, then the task will be run immediately. Value format is [ZULU](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/time/format/DateTimeFormatter.html#ISO_INSTANT) time, documented in ISO 8601.

Example of a one-time calendar

```javascript
{type: 'ONE_TIME', value: '2021-01-01T10:30:00.00Z'}
```

cron

Should be used for repeatable tasks. [UNIX](https://www.unix.com/man-page/linux/5/crontab) cron lib format is expected. Also, a timezone must be specified to run the job at a particular time of the day.

Example of a cron calendar

```javascript
{type: 'CRON', value: '* * * * *' // every minute
,timeZone: 'GMT+5:30'}
```

## Configuration

There are two ways to configure custom scheduled jobs: [lib](docs/code/stable/libraries/lib-scheduler.md) API provides methods to manipulate jobs and [config](docs/platform/stable/deployment/config.md#scheduler) file is used to configure default permanent cron jobs.

## System jobs

XP platform provides predefined system jobs, which can be enabled and overridden by user in [config](docs/platform/stable/deployment/config.md#scheduler) file. Config modification doesn’t update job nodes automatically, so make sure you’ve removed or changed old job nodes manually before any config change.

Vacuum

Deletes unused blobs and binaries from a blobstore.

> **Warning:** Make sure you have a backup of the installation available before doing a vacuum.

Predifined vacuum job properties

```properties
init-job.vacuum.enabled=false
init-job.vacuum.cron=0 5 * * *
init-job.vacuum.descriptor=com.enonic.xp.app.system:vacuum
init-job.vacuum.description=Job to run vacuum
init-job.vacuum.user=system:su
```

Common vacuum process config can be found in [Vacuum config file](docs/platform/stable/deployment/config.md#vacuum).

Audit log cleanUp

Deletes records from audit log repository.

> **Warning:** Make sure you have a backup of the installation available before running a cleanUp.

Predefined cleanUp job properties

```properties
init-job.audit-log-cleanup.enabled=false
init-job.audit-log-cleanup.cron=0 5 * * *
init-job.audit-log-cleanup.descriptor=com.enonic.xp.app.system:audit-log-cleanup
init-job.audit-log-cleanup.description=Job to clean up old audit log history
init-job.audit-log-cleanup.user=system:su
```

Common cleanup process config can be found in [Audit config file](docs/platform/stable/deployment/config.md#audit).

> **Important:** `ageThreshold` property must be set to appropriate value, otherwise nothing will be removed.

## Distributable

XP platform guarantees that a scheduled job won’t be executed by multiple threads concurrently for the cluster environment.

> **Note:** Several jobs can describe the same task descriptor, so the same code can be run by different threads simultaneously. Also, if the execution time of the task is longer than the cron period (especially important for long-term jobs) then a new task can be started before the previous is finished.

A scheduled job can be executed by any cluster node supporting an application, which contains the described task. See [task](docs/code/stable/background/tasks.md#distributable) for further explanation.
