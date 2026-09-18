<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/tasks generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/tasks.md

# Tasks

The XP framework also supports execution of asynchronous (potentially long running) background tasks.

Tasks may simply be executed as inline functions, or as named tasks. Named tasks are defined by creating a folder i.e. `src/main/resources/tasks/` in your project.

## Descriptor

Named tasks requires a descriptor file. The descriptor must be placed in task folder as follows: `src/main/resources/tasks//.xml`.

Sample descriptor

```xml
<task>
  <description>Background job</description>
  <form>
    <input type="Long" name="count">
      <label>Number of items to process</label>
      <occurrences minimum="1" maximum="1"/>
    </input>
  </form>
</task>
```

When parameters are passed to the task controller, they will be validated according to the descriptor schema.

The form element in the descriptor XML is optional, and may be left empty if the task does not accept any parameters.

## Controller

Named tasks require a controller that represents the actual code to be executed. The controller must be placed in the task folder as `src/main/resources/tasks//.js`.

A named task controller must export a run function, which will be invoked by the [task engine](/docs/platform/7.x/runtime/task-engine). once a task is executed.

The run function will receive the task parameters as a JSON object.

`taskId` is provided as a second argument of the function XP 7.13.0

Example task controller

```javascript
var taskLib = require('/lib/xp/task');

exports.run = function (params, taskId) {

    var count = params.count || 42;
    taskLib.progress({info: 'Initializing task ' + taskId});

    for (var i = 0; i < count; i++) {
        taskLib.progress({
            info: 'Processing item ' + (i + 1),
            current: i,
            total: count
        });
        processItem(i);
    }

    taskLib.progress({info: 'Task completed ' + taskId});
};
```

## Execution

Named tasks may be executed by any controller in the system. Applications may even run tasks in other applications.

Below is an example of how to run a specific task.

Sample execution of named task

```javascript
var taskLib = require('/lib/xp/task');

var taskId = taskLib.submitTask({
        descriptor: `mytask`,
        config: {
            count: 10
        }
    }
);
```

## Distributable

XP 7.6.0

Named tasks may get distributed over other cluster nodes. Cluster node can be configured to accept or decline distributable tasks execution. If multiple cluster nodes can accept a task, only one cluster node will be selected to execute it. If none of the nodes can accept a distributable task, an error will be thrown.

Distributable task gets executed with the same context (user, repository/branch) it was originally submitted.

> **Warning:** Make sure your Named task does not require a specific node to run on (i.e. it must not check for `isMaster`). If you need such check, use inline function task instead.

> **Note:** Nodes that do not accept distributable tasks execution are still capable to submit them.

> **Note:** For fine-grained control which nodes should be capable to execute distributable tasks use [Application](/docs/platform/7.x/deployment/config#application) filter config or local apps. Or disable execution of named tasks entirely on some nodes by [Task](/docs/platform/7.x/deployment/config#task) config.

## API

Tasks are capable of producing status reports during execution. This is in particular useful for long running tasks where feedback is crucial.

Additionally, tasks produce a range of pre-defined events throughout their life cycle.

For more details on tasks, visit the [task API documentation](/docs/platform/7.x/api/lib-task).
