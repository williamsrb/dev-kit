<!-- src:https://developer.enonic.com/docs/code/stable/background/tasks generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/background/tasks.md

# Tasks

The XP framework also supports execution of asynchronous (potentially long running) background tasks.

Tasks may be executed as inline functions, or as named tasks. Named tasks are defined by creating a folder, e.g. `src/main/resources/tasks/`, in your project.

## Descriptor

Named tasks requires a descriptor file. The descriptor must be placed in task folder as follows: `src/main/resources/tasks//.yaml`.

Sample descriptor

```yaml
kind: "Task"
description: "Background job"
form:
- type: "Long"
  name: "count"
  label: "Number of items to process"
  occurrences:
    min: 1
    max: 1
```

Parameters passed to the task are validated against the descriptor schema before the implementation runs.

The `form` list is optional and may be omitted if the task does not accept any parameters.

## Implementation

A named task’s implementation lives at `src/main/resources/tasks//.ts` and must export a `run` function. XP invokes `run` with the task parameters as the first argument and the assigned `taskId` as the second.

Example task implementation

```typescript
const taskLib = require('/lib/xp/task');

exports.run = (params, taskId) => {
    const count = params.count || 42;
    taskLib.progress({ info: `Initializing task ${taskId}` });

    for (let i = 0; i < count; i++) {
        taskLib.progress({
            info: `Processing item ${i + 1}`,
            current: i,
            total: count
        });
        processItem(i);
    }

    taskLib.progress({ info: `Task completed ${taskId}` });
};
```

## Execution

Named tasks may be submitted from any module in the app. Applications may even run tasks defined in other applications.

Sample execution of a named task

```typescript
const taskLib = require('/lib/xp/task');

const taskId = taskLib.submitTask({
    descriptor: 'mytask',
    config: {
        count: 10
    }
});
```

## Distributable

Named tasks may get distributed over other cluster nodes. Cluster node can be configured to accept or decline distributable tasks execution. If multiple cluster nodes can accept a task, only one cluster node will be selected to execute it. If none of the nodes can accept a distributable task, an error will be thrown.

Distributable tasks get executed with the same context (user, repository/branch) it was originally submitted.

> **Warning:** Make sure your Named task does not require a specific node to run on (i.e. it must not check for `isLeader`). If you need such check, use inline function task instead.

> **Note:** Nodes that do not accept distributable tasks execution are still capable to submit them.

> **Note:** For fine-grained control which nodes should be capable to execute distributable tasks use [Application](docs/platform/stable/deployment/config.md#application) filter config or local apps. Or disable execution of named tasks entirely on some nodes by [Task](docs/platform/stable/deployment/config.md#task) config.

## API

Tasks are capable of producing status reports during execution. This is in particular useful for long running tasks where feedback is crucial.

Additionally, tasks produce a range of pre-defined events throughout their life cycle.

For more details on tasks, visit the [Task library](docs/code/stable/libraries/lib-task.md).
