<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-scheduler generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-scheduler.md

# Scheduler API

XP 7.7.0

Functions for creating and managing scheduled jobs.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-scheduler:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import schedulerLib from '/lib/xp/scheduler';
```

## Functions

### get

Returns a scheduled job with the specified name.

Parameters

| Name | Type | Description |  |  |  |
| --- | --- | --- | --- | --- | --- |
| params | object | JSON with the parameters      Properties                  Name | Type | Attributes | Description |
| name | string | required | name of the job. |  |  |

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

| Name | Type | Description |  |  |  |
| --- | --- | --- | --- | --- | --- |
| params | object | JSON with the parameters      Properties                  Name | Type | Attributes | Description |
| name | string | required | unique job name. |  |  |
| description | string | optional | job description. |  |  |
| descriptor | string | required | descriptor of the task to be scheduled. |  |  |
| config | object | optional | config of the task to be scheduled. |  |  |
| schedule | object | required | task time run config. |  |  |
| schedule.value | string | required | schedule value according to its type. |  |  |
| schedule.type | string | required | schedule type (CRON or ONE_TIME). |  |  |
| schedule.timeZone | string | required for schedule.type = CRON | time zone of cron scheduling. It isn’t applicable to a onetime job. |  |  |
| user | string | optional | principal key of the user that submitted the task. |  |  |
| enabled | boolean | required | job is active or not. |  |  |

Returns

**object** : ([`ScheduledJob`](#scheduled_job)) Detail information for the created job.

Example

```typescript
import {create} from '/lib/xp/scheduler';

const simpleOneTimeJob = create({
    name: 'my-project',
    descriptor: 'appKey:task',
    enabled: true,
    schedule: {type: 'ONE_TIME', value: '2021-01-01T00:00:00.00Z'}
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
        c: {
            0: '1',
            1: '2'
        },
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
    createdTime: '2021-01-01T10:36:00Z',
    modifiedTime: '2016-01-01T10:36:00Z',
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

| Name | Type | Description |  |  |  |
| --- | --- | --- | --- | --- | --- |
| params | object | JSON with the parameters      Properties                  Name | Type | Attributes | Description |
| name | string | required | unique job name. |  |  |
| editor | function | required | editor callback function has an editable existing job as a param. |  |  |

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

### delete

Deletes a scheduled job.

Parameters

| Name | Type | Description |  |  |  |
| --- | --- | --- | --- | --- | --- |
| params | object | JSON with the parameters      Properties                  Name | Type | Attributes | Description |
| name | string | required | name of the job to be deleted. |  |  |

Returns

**boolean** : `true` if deleted, `false` otherwise

Example

```typescript
import {delete as deleteJob} from '/lib/xp/scheduler';

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

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| name | string | Job name |  |  |
| description | string | Job description |  |  |
| descriptor | string | descriptor of the task to be scheduled |  |  |
| config | object | config of the task to be scheduled |  |  |
| schedule | object | task time run config      Properties                Name | Type | Description |
| schedule.value | string | schedule value |  |  |
| schedule.type | string | schedule type. |  |  |
| schedule.timeZone | string | time zone of cron scheduling. It isn’t applicable to a onetime job |  |  |

user

string

principal key of the user that submitted the task

enabled

boolean

job is active or not

creator

string

principal key of user that created the task

modifier

string

principal key of the last user that modified the task

createdTime

string

time of the task creation

modifiedTime

string

time of the last task modification

lastRun

string

time of the last job run

lastTaskId

string

task id of the last job run
