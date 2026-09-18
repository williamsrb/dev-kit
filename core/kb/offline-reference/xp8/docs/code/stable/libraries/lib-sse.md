<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-sse generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-sse.md

# SSE library

Server-Sent Events functions.

## Usage

```groovy
dependencies {
  include xplibs.sse
}
```

```typescript
import sseLib from '/lib/xp/sse';
```

> **Note:** Unlike `lib-websocket`, every function in this library takes a single object parameter.

## Message shape

The `send` and `sendToGroup` functions accept a `message` object with the following optional fields:

| Name | Type | Description |
| --- | --- | --- |
| event | string | Event name. Optional. |
| data | string | Event payload. A message with no `data` does not dispatch a client event, but any `id` still updates the client’s last-event-id buffer. |
| id | string | Event id used by the client for `Last-Event-ID` reconnection tracking. |
| comment | string | SSE comment line. Ignored by clients — useful for keep-alive pings. |

## Functions

### send

Sends a message to a specific SSE connection.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params.clientId | string | Client id, captured from the `open` event in the implementation’s `sseEvent` function. |
| params.message | object | Message to send. See [Message shape](#message-shape). |

Returns

**void**

Example

```typescript
import {send} from '/lib/xp/sse';

send({clientId: clientId, message: {event: 'message', data: 'Hello!'}});
```

> **Note:** `send` is a safe no-op when the connection is closed — do not guard with `isOpen` to avoid a race.

### sendToGroup

Sends a message to all connections in a named group.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params.group | string | Group name. |
| params.message | object | Message to send. See [Message shape](#message-shape). |

Returns

**void**

Example

```typescript
import {sendToGroup} from '/lib/xp/sse';

sendToGroup({group: 'live', message: {data: 'Update'}});
```

### close

Closes an SSE connection. The connection’s `sseEvent` function will receive a `close` event.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params.clientId | string | Client id. |

Returns

**void**

Example

```typescript
import {close} from '/lib/xp/sse';

close({clientId: clientId});
```

### isOpen

Checks whether an SSE connection is still open. Use it to abort expensive work (long-running computation, large payload generation) when the client has disconnected.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params.clientId | string | Client id. |

Returns

**boolean** — `true` if the connection is still open.

Example

```typescript
import {isOpen, send} from '/lib/xp/sse';

for (let i = 0; i < 10; i++) {
    if (!isOpen({clientId: clientId})) {
        break;
    }
    const data = computeExpensiveData(i);
    send({clientId: clientId, message: {event: 'update', data: data}});
}
```

### addToGroup

Adds a connection to a named group.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params.group | string | Group name. |
| params.clientId | string | Client id. |

Returns

**void**

Example

```typescript
import {addToGroup} from '/lib/xp/sse';

addToGroup({group: 'live', clientId: clientId});
```

### removeFromGroup

Removes a connection from a named group.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params.group | string | Group name. |
| params.clientId | string | Client id. |

Returns

**void**

Example

```typescript
import {removeFromGroup} from '/lib/xp/sse';

removeFromGroup({group: 'live', clientId: clientId});
```

### getGroupSize

Returns the number of connections currently in a group.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params.group | string | Group name. |

Returns

**number**

Example

```typescript
import {getGroupSize} from '/lib/xp/sse';

const count = getGroupSize({group: 'live'});
```
