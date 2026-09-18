<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-event generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-event.md

# Event API

This API provides functions to create and listen to instance local or cluster distributed events.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-event:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import eventLib from '/lib/xp/event';
```

> **Note:** Several standard XP APIs already produce and publish events. For more details, check out the [node API](/docs/platform/7.x/api/lib-node#events), [repository API](/docs/platform/7.x/api/lib-repo#events), and [task API](/docs/platform/7.x/api/lib-task#events)

## Functions

### listener

Creates an event listener

Parameters

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| type | string | Works like a Java Pattern, with two key differences: `.` is treated as a literal dot, not a wildcard. `*` acts as `.*`, matching any sequence of characters. |
| callback | function | Callback event listener |
| localOnly | boolean | Local events only (default to false) |

Returns

`null`

Example

Adding a listener that logs the event

```typescript
eventLib.listener({
    type: 'node.*',
    localOnly: false,
    callback: (event) => {
        log.info('event: %s', JSON.stringify(event));
    }
});
```

### send

Sends a custom event. All custom events are prefixed with `custom.`.

Parameters

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| type | string | Event type |
| distributed | boolean | `true` if it should be distributed in cluster |
| data | object | Additional data for event. |

Returns

`null`

Example

Send a custom event into the system

```typescript
eventLib.send({
    type: 'myEvent',
    distributed: false,
    data: {
        a: 1,
        b: 2
    }
});
```
