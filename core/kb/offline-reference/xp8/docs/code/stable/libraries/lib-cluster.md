<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-cluster generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-cluster.md

# Cluster library

This API provides cluster related functions.

## Usage

```groovy
dependencies {
  include xplibs.cluster
}
```

```typescript
import clusterLib from '/lib/xp/cluster';
```

## Functions

### isLeader

Tests whether the current node is the leader for the calling application. Useful for guarding work that should run on a single node — scheduled initialization, one-shot tasks, or event handlers that must not fire on every cluster node.

Parameters

None

Returns

**boolean** : `true` if the current node is the leader; `false` otherwise.

Examples

Initialize data only on the leader node

```typescript
import {isLeader} from '/lib/xp/cluster';
if (isLeader()) {
    initializeRepo();
}
```

Run a named task only on the leader

```typescript
import {isLeader} from '/lib/xp/cluster';
import {submitTask} from '/lib/xp/task';

if (isLeader()) {
    submitTask({
        descriptor: 'longRunningTask'
    });
}
```

Handle an event only on the leader

```typescript
import {isLeader} from '/lib/xp/cluster';
import {listener} from '/lib/xp/event';

listener({
    type: 'node.pushed',
    localOnly: false,
    callback: (event) => {
        if (isLeader()) {
            log.info('event: %s', JSON.stringify(event));
        }
    }
});
```

### isMaster

> **Warning:** Deprecated since XP 8 — use [isLeader](#isleader) instead.

Tests whether the current node is the master node in the cluster. Same signature and return type as `isLeader`.

```typescript
import {isMaster} from '/lib/xp/cluster';
if (isMaster()) {
    initializeRepo();
}
```
