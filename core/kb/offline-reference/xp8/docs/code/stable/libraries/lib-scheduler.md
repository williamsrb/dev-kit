<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-scheduler generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-scheduler.md

# Scheduler library

Functions for creating and managing scheduled jobs.

## Usage

```groovy
dependencies {
  include xplibs.scheduler
}
```

```typescript
import schedulerLib from '/lib/xp/scheduler';
```

## Functions

### get

Returns a scheduled job with the specified name.

Parameters

`get()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Name of the job. |

Returns

**object** : ([`ScheduledJob`](#scheduled_job)) Detail information for the job. Or null if the job could not be found.

Example

Obtains details of a scheduled job:

```typescript
import {get as getJob} from '/lib/xp/scheduler';

const job = getJob({ name: 'myjob' });

if (job) {
  log.info('Job is found: %s', JSON.stringify(job, null, 4));
} else {
  log.info('Job not found');
}
```

Return value:

```typescript
const expected = {
    name: 'myjob',
    descriptor: 'com.enonic.app.myapp:mytask',
    description: 'cron job description',
    enabled: true,
    config: {
        a: 1,
        b: 'value',
        c: {
            d: {
                e: 3.6,
                f: true
            }
        }
    },
    user: 'user:system:user',
    creator: 'user:system:creator',
    modifier: 'user:system:creator',
    createdTime: '2016-11-02T10:36:00Z',
    modifiedTime: '2016-11-02T10:36:00Z',
    lastRun: '2021-02-25T10:44:33.170079900Z',
    lastTaskId: 'task-id',
    schedule: {
        value: '* * * * *',
        type: 'CRON',
        timeZone: 'GMT+2:00'
    }
};
```

### list

Returns the list of scheduled jobs.

Returns

**Array** : ([`ScheduledJob[]`](#scheduled_job)) List of all scheduled jobs.

Example

Obtains list of existing jobs:

```typescript
import {list} from '/lib/xp/scheduler';

const jobs = list();
```

Return value:

```typescript
const expected = [
  {
        name: 'job1',
        descriptor: 'appKey:task',
        description: 'job description',
        enabled: true,
        config: {
            a: 1
        },
        user: 'user:system:user',
        creator: 'user:system:creator',
        modifier: 'user:system:creator',
        createdTime: '2016-11-02T10:36:00Z',
        modifiedTime: '2016-11-02T10:36:00Z',
        lastRun: '2021-02-25T10:44:00.170079900Z',
        lastTaskId: 'task-id',
        schedule: {
            value: '* * * * *',
            timeZone: 'GMT+05:30',
            type: 'CRON'
        }
    },
    {
        name: 'job2',
        descriptor: 'appKey:task',
        description: 'job description',
        enabled: false,
        config: { },
        user: 'user:system:user',
        creator: 'user:system:creator',
        modifier: 'user:system:creator',
        createdTime: '2021-02-02T10:36:00Z',
        modifiedTime: '2021-02-02T10:36:00Z',
        schedule: {
            value: '2012-01-01T00:00:00Z',
            type: 'ONE_TIME'
        }
    }
];
```

### create

Creates a scheduled job.

> **Note:** This function returns immediately.

Parameters

`create()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Unique job name. |
| description | string | **Optional.** Job description. |
| descriptor | string | Descriptor of the task to be scheduled. |
| config | object | **Optional.** Config passed to the scheduled task. |
| schedule | [Schedule](#schedule-type) | When the task runs. |
| user | string | **Optional.** Principal key of the user that submitted the task. |
| enabled | boolean | Whether the job is active. |

Returns

**object** : ([`ScheduledJob`](#scheduled_job)) Detail information for the created job.

Example

```typescript
import {create} from '/lib/xp/scheduler';

const simpleOneTimeJob = create({
    name: 'my-project',
    descriptor: 'appKey:task',
    enabled: true,
    schedule: {type: 'ONE_TIME', value: '2012-01-01T00:00:00.00Z'}
});

const extendedCronJob = create({
    name: 'myjob',
    descriptor: 'appKey:task',
    description: 'job description',
    user: 'user:system:user',
    enabled: true,
    config: {
        a: 1,
        b: 2,
        c: ['1', '2'],
        d: {
            e: {
                f: 3.6,
                g: true
            }
        }
    },
    schedule: {type: 'CRON', value: '* * * * 5', timeZone: 'GMT-2:00'}
});
```

Return value:

```typescript
const expectedSimpleOneTimeJob = {
    name: 'my-project',
    descriptor: 'appKey:task',
    enabled: true,
    config: {},
    creator: 'user:system:creator',
    modifier: 'user:system:creator',
    createdTime: '2016-11-02T10:36:00Z',
    modifiedTime: '2016-11-02T10:36:00Z',
    schedule: {
        value: '2012-01-01T00:00:00Z',
        type: 'ONE_TIME'
    }
}

const expectedExtendedCronJob = {
    name: 'myjob',
    descriptor: 'appKey:task',
    description: 'job description',
    enabled: true,
    config: {
        a: 1,
        b: 2,
        c: ['1', '2'],
        d: {
            e: {
                f: 3.6,
                g: true
            }
        }
    },
    user: 'user:system:user',
    creator: 'user:system:creator',
    modifier: 'user:system:creator',
    createdTime: '2016-11-02T10:36:00Z',
    modifiedTime: '2016-11-02T10:36:00Z',
    schedule: {
        value: '* * * * 5',
        timeZone: 'GMT-02:00',
        type: 'CRON'
    }
}
```

### modify

Modifies a job.

> **Note:** The previous task will be rescheduled, `lastRun` and `lastTaskId` properties will be cleaned.

Parameters

`modify()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Unique job name. |
| editor | function | Editor callback. Receives the existing job as an editable object and returns it. See the example. |

Returns

**object** : ([`ScheduledJob`](#scheduled_job)) Detail information for the modified job.

Example

```typescript
import {modify} from '/lib/xp/scheduler';

const result = modify({
    name: 'myjob',
    editor: (edit) => {
        edit.descriptor = 'appKey:new-task';
        edit.description = 'new job description';
        edit.user = 'user:system:new-user';
        edit.enabled = false;
        edit.config = {
            a1: 3
        };
        edit.schedule = {type: 'CRON', value: '* * * * *', timeZone: 'GMT+5:30'};

        return edit;
    }
});
```

Return value:

```typescript
const resultExpected = {
    name: 'myjob',
    descriptor: 'appKey:new-task',
    description: 'new job description',
    enabled: false,
    config: {
        a1: 3
    },
    user: 'user:system:new-user',
    creator: 'user:system:creator',
    modifier: 'user:system:modifier',
    createdTime: '2016-11-02T10:36:00Z',
    modifiedTime: '2021-02-25T10:44:33.170079900Z',
    schedule: {
        value: '* * * * *',
        timeZone: 'GMT+05:30',
        type: 'CRON'
    }
}
```

### deleteJob

Deletes a scheduled job.

> **Note:** Renamed from `delete` to avoid the JavaScript reserved word. The old `delete` export is still available for backward compatibility.

Parameters

`deleteJob()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | Name of the job to delete. |

Returns

**boolean** : `true` if deleted, `false` otherwise

Example

```typescript
import {deleteJob} from '/lib/xp/scheduler';

const result = deleteJob({
    name: 'myjob'
});

if (result) {
    log.info('Job deleted');
} else {
    log.info('Job was not found');
}
```

## Type Definitions

### ScheduledJob

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| name | string | Job name. |
| description | string | Job description. |
| descriptor | string | Descriptor of the scheduled task. |
| config | object | Config passed to the scheduled task. |
| schedule | [Schedule](#schedule-type) | When the task runs. |
| user | string | Principal key of the user that submitted the task. |
| enabled | boolean | Whether the job is active. |
| creator | string | Principal key of the user that created the task. |
| modifier | string | Principal key of the last user that modified the task. |
| createdTime | string | Time of the task creation. |
| modifiedTime | string | Time of the last task modification. |
| lastRun | string | Time of the last job run. |
| lastTaskId | string | Task id of the last job run. |

### Schedule

Properties

| Name | Type | Description |
| --- | --- | --- |
| value | string | Schedule value, in the format required by `type`. |
| type | string | Schedule type: `CRON` or `ONE_TIME`. |
| timeZone | string | Time zone of the cron schedule. Required when `type` is `CRON`; not applicable to one-time jobs. |
