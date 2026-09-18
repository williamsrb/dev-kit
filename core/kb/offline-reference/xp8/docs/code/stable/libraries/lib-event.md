<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-event generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-event.md

# Event library

This API provides functions to create and listen to instance local or cluster distributed events.

## Usage

```groovy
dependencies {
  include xplibs.event
}
```

```typescript
import eventLib from '/lib/xp/event';
```

> **Note:** Several standard XP APIs already produce and publish events. For more details, check out the [Node library](docs/code/stable/libraries/lib-node.md#events), [Repo library](docs/code/stable/libraries/lib-repo.md#events), and [Task library](docs/code/stable/libraries/lib-task.md#events)

## Functions

### listener

Registers an event listener that fires for events whose type matches the given pattern.

Parameters

`listener()` takes a single `ListenerParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| type | string | Event type pattern. Works like a Java pattern, with two key differences: `.` is treated as a literal dot (not a wildcard), and `****`** acts as `.`**, matching any sequence of characters. |
| callback | function | Function invoked for each matching event. Receives a single argument, an [EnonicEvent](#enonic-event) object. |
| localOnly | boolean | **Optional.** When `true`, only events originating on the current node are delivered. Defaults to `false`. |

Returns

**void**

Example

Adding a listener that logs every node event

```typescript
import {listener} from '/lib/xp/event';

listener({
    type: 'node.*',
    localOnly: false,
    callback: (event) => {
        log.info('event: %s', JSON.stringify(event));
    }
});
```

### send

Sends a custom event. The supplied `type` is automatically prefixed with `custom.` before the event is published.

Parameters

`send()` takes a single `SendParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| type | string | Event type. Will be published as `custom.<type>`. |
| distributed | boolean | **Optional.** When `true`, the event is broadcast to every node in the cluster. Defaults to `false`. |
| data | object | **Optional.** Additional data to attach to the event payload. |

Returns

**void**

Example

Send a custom event into the system

```typescript
import {send} from '/lib/xp/event';

send({
    type: 'myEvent',
    distributed: false,
    data: {
        a: 1,
        b: 2
    }
});
```

## Type Definitions

### EnonicEvent

The object passed to a [`listener`](#listener) callback for each matching event.

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | Event type, for example `node.pushed` or `custom.myEvent`. |
| timestamp | number | Time the event was published, in milliseconds since the epoch. |
| localOrigin | boolean | `true` if the event was published on the current node, `false` if it was received from another cluster node. |
| distributed | boolean | `true` if the event was distributed across the cluster. |
| data | object | Event payload. Shape depends on the event `type`; for built-in node events, see [Node library](docs/code/stable/libraries/lib-node.md#events). |
