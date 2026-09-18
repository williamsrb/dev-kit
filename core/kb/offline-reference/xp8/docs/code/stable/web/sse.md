<!-- src:https://developer.enonic.com/docs/code/stable/web/sse generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/sse.md

# Server-Sent Events

Server-Sent Events (SSE) provide one-way streaming from server to client over HTTP.

> **Warning:** An SSE stream keeps an HTTP connection open for its entire lifetime. Over HTTP/1.x, browsers cap concurrent connections per origin to a small number (typically 6 in current Chrome, Firefox, and Safari), so a handful of open SSE streams — across tabs or endpoints on the same origin — can saturate that budget and block the rest of the page’s requests. Serve SSE over HTTP/2 (or HTTP/3), where many streams multiplex on a single connection and this limit does not apply.

## SSE

An implementation becomes an SSE endpoint by returning an `sse` object from its `GET` function. Each connected client reuses the same module instance; per-connection state lives in `attributes`.

```typescript
exports.GET = (req) => {
    return {
        sse: {
            attributes: { startedAt: Date.now() }, (1)
            retry: 5000,                           (2)
            timeout: 0                             (3)
        }
    };
};
```

| ****1** | Per-connection object, exposed as `event.attributes` on every lifecycle event. Set once at SSE setup and immutable thereafter — events always see the original snapshot. Defaults to an empty object if omitted. |
| --- | --- |
| ****2** | Client reconnect hint in milliseconds. Optional. Default: `-1`, which omits the hint and lets the browser pick its own. |
| ****3** | Async context timeout in milliseconds. Optional. Default: `0`, which means no timeout. |

The implementation can react to lifecycle events by exporting an `sseEvent` function:

```typescript
exports.sseEvent = (event) => {
    if (event.type === 'open') {
        // send a message back using event.clientId, or add it to a group for later broadcasts
    } else if (event.type === 'close') {
        // optional teardown — group membership is cleaned up automatically
    }
};
```

Lifecycle event:

```JSON
{
    "type": "open",                            (1)
    "clientId": "f1c2...",                     (2)
    "lastEventId": "42",                       (3)
    "attributes": { "startedAt": 1700000000 }  (4)
}
```

| ****1** | Event type. One of `open`, `close`, `timeout`, `error`. `close` is always the terminal event — it fires after `timeout` and after `error`, so use it for teardown and reserve `timeout`/`error` for diagnostics. |
| --- | --- |
| ****2** | Server-generated id of the SSE connection. Capture it on `open` and use it with `lib/xp/sse` to push messages. |
| ****3** | Value of the client’s `Last-Event-ID` header on reconnection, or `null` on the first connect. Use it to resume a stream from a known point. |
| ****4** | The same `attributes` object passed to the response, shared across the connection’s lifetime. |

## Sending messages

A connection is identified by `event.clientId`, delivered to the `sseEvent` function when the connection opens. The example below sends a welcome message back to the client that just connected:

```typescript
const sseLib = require('/lib/xp/sse');

exports.sseEvent = (event) => {
    if (event.type === 'open') {
        sseLib.send({
            clientId: event.clientId,
            message: { event: 'welcome', data: 'Hello!' }
        });
    }
};
```

`message.id` updates the client’s last-event-id buffer for reconnects. `message.comment` emits an SSE comment line — useful for keep-alive pings. A message with no `data` does not dispatch a client event but any `id` still updates the buffer.

To address a client from outside the `sseEvent` function, do not store `event.clientId` in module-scope state — module code runs multi-threaded/multi-engine and ad-hoc shared collections of ids are not safe. Use one of the following instead:

- For a **task** or other background job, capture the `clientId` when the task is started and hold it in the task’s own local scope. Each task instance then targets exactly the connection it was started for.

- For an **event listener**, use named groups: add the connection on `open`, then call `sendToGroup` from the listener.

```typescript
const sseLib = require('/lib/xp/sse');

exports.sseEvent = (event) => {
    if (event.type === 'open') {
        sseLib.addToGroup({ group: 'live', clientId: event.clientId });
    }
};

// from an event listener:
sseLib.sendToGroup({ group: 'live', message: { data: 'Update' } });
```

See [SSE library](docs/code/stable/libraries/lib-sse.md) for the full reference.

> **Note:** `send` is a safe no-op for closed connections — do not guard with `isOpen` to avoid races. Use `isOpen` to abort expensive work when a client has disconnected.
