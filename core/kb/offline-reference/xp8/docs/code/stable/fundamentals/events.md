<!-- src:https://developer.enonic.com/docs/code/stable/fundamentals/events generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/fundamentals/events.md

# Events

Send and listen to local or cluster wide events

## Introduction

The XP framework enable developers to create and/or listen to events. Events may be local (within a single server) or cluster wide (distributed to all servers within a cluster). In addition to application specific events, XP itself produces a range of standard events.

## Use cases

The use cases for events are limitless, but the most common are:

- Cache invalidation

- Notifications (i.e. notify clients connected to any server in the cluster via Websocket)

- Job triggering

## Local vs distributed semantics

- `send({distributed: false})` (default) — fires only on the node that produced the event; use for in-process signalling like per-node cache eviction.

- `send({distributed: true})` — broadcasts to every member of the cluster; use for cross-node cache invalidation, multi-node WebSocket fanout, or any side effect that has to run on every node.

- `listener({localOnly: true})` — filters out events that originated on a remote node; use when a side effect should run exactly once on the originating node.

- The event object’s `localOrigin` and `distributed` flags let a listener branch on origin without `localOnly`.

> **Important:** Event delivery is best-effort and fire-and-forget — no persistence, no replay, no acknowledgement. A node that is down or partitioned at broadcast time misses the event entirely.

## Threading and ordering

`Each event is handed to a single event worker thred before walking the listener list, so the publishing thread returns as soon as the event is queued.

- Listeners must not block — the dispatch thread is shared, and a slow listener backs up every other listener on the node.

- On a single node, FIFO holds — events published in sequence on the same node are delivered in that order to a listener that matches both.

- Across cluster nodes events from the same nodes are ordered but from different nodes can arrive in either order on any third node.

- Order between listeners is unspecified.

## Standard event catalog

| Type pattern | Origin | What it signals |
| --- | --- | --- |
| `node.*` | core-repo | Node lifecycle: `node.created`, `node.updated`, `node.deleted`, `node.pushed`, `node.duplicated`, `node.moved`, `node.sorted`, `node.permissionsUpdated`. |
| `repository.*` | core-repo | Repository lifecycle: `repository.created`, `repository.updated`, `repository.deleted`, `repository.restored`, `repository.restoreInitialized`. |
| `task.*` | core-task | Task lifecycle: `task.submitted`, `task.updated`, `task.finished`, `task.failed`, `task.removed`. |
| `application`, `application.cluster` | core-app | Application install / start / stop and cluster install events; the action — `INSTALLED`, `STARTED`, `STOPPED`, `UNINSTALLED`, `state`, … — is carried in the payload’s `eventType` field, not the type string. |
| `custom.*` | user code | Anything published through lib-event’s `send()`. The `custom.` prefix is added automatically. |

Per-type payload details belong on the corresponding library page ([Node](docs/code/stable/libraries/lib-node.md#events), [Repo](docs/code/stable/libraries/lib-repo.md#events), [Task](docs/code/stable/libraries/lib-task.md#events)).

## Custom event naming

Custom events go through `eventLib.send(…​)`, which prepends `custom.` automatically — `send({type: 'foo'})` is delivered as `custom.foo`. Namespace by application key to avoid collisions when multiple apps share a cluster.

```typescript
import eventLib from '/lib/xp/event';

eventLib.send({
    type: 'com.example.app.somethingHappened',
    distributed: true,
    data: { id: 'abc-123' }
});
// delivered as 'custom.com.example.app.somethingHappened'
```

## Common patterns

### Cluster-wide cache invalidation

A write on any node evicts the affected key on every node.

```typescript
eventLib.listener({
    type: 'custom.com.example.app.cache.invalidate',
    callback: (event) => cache.delete(event.data.key as string)
});

eventLib.send({
    type: 'com.example.app.cache.invalidate',
    distributed: true,
    data: { key }
});
```

### WebSocket fanout across the cluster

A producer on any node can push to clients connected to whichever node terminated their socket.

```typescript
eventLib.listener({
    type: 'custom.com.example.app.feed.message',
    callback: (event) => websocketLib.sendToGroup('live-feed', JSON.stringify(event.data))
});

eventLib.send({
    type: 'com.example.app.feed.message',
    distributed: true,
    data: { message }
});
```

## Library

For implementation details, please visit the [event library](docs/code/stable/libraries/lib-event.md) documentation.
