<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-task generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-task.md

# Task library

Functions for execution of asynchronous tasks.

## Usage

```groovy
dependencies {
  include xplibs.task
}
```

```typescript
import taskLib from '/lib/xp/task';
```

## Events

Usage of this API produces the following events:

| Event | Occurs when |
| --- | --- |
| task.submitted | a task is submitted |
| task.updated | a task is updated |
| task.removed | a task is removed |
| task.finished | a task completes |
| task.failed | a task fails |

For more information on events, check out the [Event library](docs/code/stable/libraries/lib-event.md)

## Functions

### get

Returns the current state and progress details for the specified task.

Parameters

Takes a single positional argument: `taskId` (string) — the id of the task to look up.

Returns

**object** : ([`TaskInfo`](#task-info)) Detail information for the task. Or null if the task could not be found.

Example

Obtains details for an active task:

```typescript
import {get as getTask} from '/lib/xp/task';

const taskInfo = getTask('7ca603c1-3b88-4009-8f30-46ddbcc4bb19');

if (taskInfo) {
  log.info('Current task state = %s', taskInfo.state);
} else {
  log.info('Task not found');
}
```

Return value:

```typescript
const expected = {
  description: "Long running task",
  id: "7ca603c1-3b88-4009-8f30-46ddbcc4bb19",
  name: "task-7ca603c1-3b88-4009-8f30-46ddbcc4bb19",
  state: "RUNNING",
  application: "com.enonic.myapp",
  user: "user:store:me",
  startTime: "2017-10-01T09:00:00Z",
  progress: {
    info: "Processing item 33",
    current: 33,
    total: 42
  }
};
```

### isRunning

Checks if any task with the given name or id is currently running.

Parameters

Takes a single positional argument: `task` (string) — the name or id of the task.

Returns

**boolean** : `true` if there is a task with the specified name or id, and state 'RUNNING'; `false` otherwise.

Example

Check if a task is currently running:

```typescript
import {isRunning} from '/lib/xp/task';

if (!isRunning('com.enonic.myapp:clean-up-task')) {
  log.info('Start task...');
} else {
  log.info('Task already running');
}
```

### list

Returns the list of active tasks with their current state and progress details. On clustered environments aggregated list is returned.

Parameters

`list()` takes a single, optional `ListTasksParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | **Optional.** Filter by name. |
| state | [`TaskStateType`](#task-state-type) | **Optional.** Filter by task state. |

Returns

**Array** : ([`TaskInfo[]`](#task-info)) List with task information for every task.

Example

1. Obtains list of active tasks:

```typescript
import {list} from '/lib/xp/task';

const tasks = list();
```

Return value:

```typescript
const expected = [
  {
    description: "Long running task",
    id: "7ca603c1-3b88-4009-8f30-46ddbcc4bb19",
    name: "task-7ca603c1-3b88-4009-8f30-46ddbcc4bb19",
    state: "RUNNING",
    application: "com.enonic.app1",
    user: "user:store:user1",
    startTime: "2017-10-01T09:00:00Z",
    progress: {
      info: "Processing item 33",
      current: 33,
      total: 42
    }
  },
  {
    description: "Update statistics",
    id: "b6173bcb-bf54-409b-aa6b-96ae6fcec263",
    name: "task-b6173bcb-bf54-409b-aa6b-96ae6fcec263",
    state: "FINISHED",
    application: "com.enonic.app2",
    user: "user:store:user2",
    startTime: "2017-10-02T09:00:00Z",
    progress: {
      info: "Work completed",
      current: 0,
      total: 0
    }
  },
  {
    description: "Import remote data",
    id: "e1f57280-d672-4cd8-b674-98e26e5b69ae",
    name: "task-e1f57280-d672-4cd8-b674-98e26e5b69ae",
    state: "FAILED",
    application: "com.enonic.app3",
    user: "user:store:user3",
    startTime: "2017-10-03T09:00:00Z",
    progress: {
      info: "Fetching data",
      current: 33,
      total: 100
    }
  }
];
```

2. Obtains list of running tasks with a given name and state:

```typescript
import {list} from '/lib/xp/task';

const tasks = list({
  name: "com.enonic.myapp:clean-up",
  state: "RUNNING"
});
```

Return value:

```typescript
const expected = [
  {
    description: "Long running task",
    id: "7ca603c1-3b88-4009-8f30-46ddbcc4bb19",
    name: "com.enonic.myapp:clean-up",
    state: "RUNNING",
    application: "com.enonic.myapp",
    user: "user:store:user",
    startTime: "2017-10-01T09:00:00Z",
    progress: {
      info: "Processing item 33",
      current: 33,
      total: 42
    }
  }
];
```

### progress

Reports progress information from an executing task. This function can only be called within the context of a task function, otherwise it will fail and throw an exception.

Parameters

`progress()` takes a single `TaskProgressParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| current | number | **Optional.** Integer value representing the number of items that have been processed in the task. |
| total | number | **Optional.** Integer value representing the total number of items to process in the task. |
| info | string | **Optional.** Text describing the current progress for the task. |

Returns

**void**

Example

Execute task and keep taskId for polling status:

```typescript
import {executeFunction, progress} from '/lib/xp/task';

const taskId = executeFunction({
  description: 'Background task',
  func: () => {

    progress({info: 'Initializing task'});

    for (const i of Array(10).keys()) {
      progress({
        info: 'Processing item ' + (i + 1),
        current: i,
        total: 10
      });

      processItem(i);
    }

    progress({info: 'Task completed'});
  }
});
```

### sleep

Causes the current execution thread to sleep (temporarily cease execution) for the specified number of milliseconds.

Parameters

Takes a single positional argument: `timeMillis` (number) — the length of time to sleep in milliseconds.

Returns

**void**

Example

Execute task and keep taskId for polling status:

```typescript
import {sleep} from '/lib/xp/task';

let retries = 3;
let result = fetchRemoteData();

while (!result && retries > 0) {
  // wait half a second before retrying
  sleep(500);
  retries -= 1;
  result = fetchRemoteData();
}
```

### executeFunction

Executes a function in the background. Returns an id representing the task of execution.

This function returns immediately. The callback function will be executed asynchronously.

Parameters

`executeFunction()` takes a single `ExecuteFunctionParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| description | string | Text describing the task to be executed. |
| func | function | Callback function to be executed asynchronously. |

Returns

**string** : Id of the task that will be executed.

Example

Execute task function and keep taskId for polling status:

```typescript
import {executeFunction} from '/lib/xp/task';

const taskId = executeFunction({
  description: 'Background function',
  func: () => {
    longRunningFunction();
  }
});
```

### submitTask

Submits a task to be executed in the background and returns an id representing the task.

> **Note:** This function returns immediately. The task will be executed asynchronously.

> **Tip:** lib-task prior version 7.6 does not submit distributable named tasks, instead task always gets executed locally. Recompile your application with the newer library version in order for tasks to be distributable.

Parameters

`submitTask()` takes a single `SubmitTaskParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| descriptor | string | Descriptor of the task to execute. Descriptor can be relative to the current application, or a fully qualified task descriptor name (`<appname>:<taskname>`). |
| name | string | **Optional.** Name of the task which appears in task info. If not specified, the descriptor key will be used instead. |
| config | object | **Optional.** Configuration parameters to pass to the task to be executed. The object must be valid according to the schema defined in the form of the task descriptor XML. |

Returns

**string** : Id of the task that will be executed.

Example

Execute task, located in the current app, by name:

```typescript
import {submitTask} from '/lib/xp/task';

const taskId = submitTask({
  descriptor: 'job42',
  config: {
    count: 123
  }
});
```

Execute a task located in a different app:

```typescript
import {submitTask} from '/lib/xp/task';

const taskId = submitTask({
  descriptor: 'com.enonic.app.myapp:work',
  config: {}
});
```

## Type Definitions

### TaskInfo

Properties

| Name | Type | Description |
| --- | --- | --- |
| id | string | Task id. |
| name | string | Task name. |
| description | string | Task description. |
| state | [`TaskStateType`](#task-state-type) | Task state. |
| application | string | Application containing the callback function to run. |
| user | [UserKey](docs/code/stable/fundamentals/types.md#user-key) | Key of the user that submitted the task. |
| startTime | string | Time when the task was submitted (in ISO-8601 format). |
| progress | [`TaskProgress`](#task-progress) | Progress information provided by the running task. |
| node | string | **Optional.** Identifier of the cluster node where the task is running. Absent when no cluster is configured. |

### TaskProgress

Properties

| Name | Type | Description |
| --- | --- | --- |
| current | number | Integer value representing the number of items that have been processed in the task. |
| total | number | Integer value representing the total number of items to process in the task. |
| info | string | Text describing the current progress for the task. |

### TaskStateType

One of `'WAITING'`, `'RUNNING'`, `'FINISHED'`, or `'FAILED'`.
