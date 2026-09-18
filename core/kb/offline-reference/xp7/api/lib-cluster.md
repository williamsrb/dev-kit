<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-cluster generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-cluster.md

# Cluster API

This API provides cluster related functions.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-cluster:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import clusterLib from '/lib/xp/cluster';
```

## Functions

### isMaster

Tests whether the current node is the master node in a cluster. A cluster with multiple master nodes will only return true on the elected node.

Parameters

None

Returns

**boolean** : `true` if the current node is master; `false` otherwise.

Examples

Initialize data only on the master node

```typescript
import {isMaster} from '/lib/xp/cluster';
if (isMaster()) {
    initializeRepo();
}
```

Run task only on master

```typescript
import {isMaster} from '/lib/xp/cluster';
import {submit} from '/lib/xp/task';

if (isMaster() {
    const taskId = submit({
        description: 'Master only task',
        task: () => {
          longRunningTask();
        }
    });
})
```

Catch event and execute something only on master

```typescript
import {isMaster} from '/lib/xp/cluster';
import {listener} from '/lib/xp/event';

listener({
    type: 'node.pushed',
    localOnly: false,
    callback: (event) => {
        if(isMaster()) {
            log.info('event: %s', JSON.stringify(event));
        }
    }
});
```
