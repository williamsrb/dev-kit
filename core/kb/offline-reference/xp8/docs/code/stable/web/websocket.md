<!-- src:https://developer.enonic.com/docs/code/stable/web/websocket generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/websocket.md

# HTTP WebSockets

HTTP WebSockets enable two-way communication with HTTP clients

## Websockets

Websocket support allows a service to act as a websocket channel that you can connect to from a web-browser.

A `GET` method must be implemented to handle initialization of the websocket. It can supply `data` object that will be available via `event.data`.

```javascript
// Create a websocket if websocket request.
exports.GET = function (req) {

  if (!req.webSocket) {
    return {
      status: 404
    };
  }

  return {
    webSocket: {
      data: {
        user: "test"
      },
      subProtocols: ["text"]
    }
  };
};
```

A websocket event handler named `webSocketEvent` is required. It will be called for every websocket event from a client. See example below.

```javascript
// Listen to a websocket event
exports.webSocketEvent = function (event) {

  if (event.type == 'open' && event.data.user == 'test') {
    // Do something on open
  }

  if (event.type == 'message') {
    // Do something on message received
  }

  if (event.type == 'close') {
    // Do something on close
  }

};
```

Event object example:

```JSON
  {
    "type": "message",  (1)
    "session": {
      "id": "7",   (2)
      "path": "/",   (3)
      "params": {},   (4)
      "user": {   (5)
        "key": "user:system:user",
        "displayName": "User",
        "modifiedTime": "1970-01-01T00:00:00Z",
        "disabled": false,
        "login": "usr",
        "idProvider": "system",
        "email": "email@example.com"
      }
    },
    "data": {   (6)
      "field": "value"
    },
    "error": "",   (7)
    "closeReason":  1000,   (8)
    "message": "Hello World"   (9)
  }
```

| ****1** | Event type. Can be one of `OPEN`, `CLOSE`, `ERROR`, `MESSAGE`. |
| --- | --- |
| ****2** | WebSocket session id. |
| ****3** | Path of the request when WebSocket was opened. |
| ****4** | Name/value pairs of the query/form parameters from the request when WebSocket was opened. |
| ****5** | Authenticated user data when WebSocket was opened, if available. |
| ****6** | Data returned from the WebSocket `GET` function. |
| ****7** | Error message, if available. |
| ****8** | WebSocket Close reason code, if available. |
| ****9** | WebSocket message, if available. |

Below is an example of a simple chat using the [Websocket library](docs/code/stable/libraries/lib-websocket.md) for sending messages back and adding/removing clients in groups. Adding to groups allows for multicast message sending.

```javascript
// Lib that contains websocket functions.
var webSocketLib = require('/lib/xp/websocket');

// Listen to a websocket event
exports.webSocketEvent = function (event) {

  if (event.type == 'open') {
    // Send message back to client
    webSocketLib.send(event.session.id, 'Welcome to our chat ' + event.session.user ? event.session.user.displayName : 'anonymous' );

    // Add client into a group
    webSocketLib.addToGroup('chat', event.session.id);

    log.info(`New group size ${webSocketLib.getGroupSize('chat')}`);
  }

  if (event.type == 'message') {
    // Propagate message to group
    webSocketLib.sendToGroup('chat', event.message);
  }

  if (event.type == 'close') {
    log.info(`User left the chat`);
  }

};
```

## Origin check

WebSockets do not follow the same-origin policy that browsers enforce on regular HTTP requests, which means a page on any origin can open a WebSocket to your application. The platform mitigates this by checking the request’s `Origin` header against the host the request arrived on before completing the handshake.

The default rules, applied when a controller does not supply its own `checkOrigin` function:

- No `Origin` header — accepted. Non-browser clients (`curl`, native apps, server-to-server) omit `Origin`, and they are not the cross-site-WebSocket-hijacking threat model.

- `Origin` matches the request’s own scheme/host/port (with RFC 6454 default-port normalisation) — accepted.

- Anything else, including the literal opaque origin `null` — rejected with HTTP `403`.

To allow other origins, or to apply application-specific logic, return a `checkOrigin` function on the `webSocket` config. It receives the raw `Origin` header value (or `null` when absent) and must return a boolean.

```javascript
// Allow only specific origins to open the WebSocket
exports.GET = function (req) {

  if (!req.webSocket) {
    return { status: 404 };
  }

  return {
    webSocket: {
      subProtocols: ['text'],
      checkOrigin: function (origin) {
        return origin === 'https://app.example.com'
            || origin.endsWith('.example.com');
      }
    }
  };
};
```

The function runs synchronously during the handshake, before any `webSocketEvent` callback. It should be a pure function of the `origin` string; capture any per-request data with a closure inside the `GET` handler. A function that throws or returns a non-boolean rejects the upgrade.

## HTTP session binding

A WebSocket starts as a regular HTTP request, and that request may run within an HTTP session — typically when the user is logged in. Once the socket is established, its traffic no longer passes through the HTTP layer, so out of the box the session and the socket would know nothing about each other. Three optional `webSocket` response parameters control how the two are bound:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `terminateOnSessionExit` | boolean | `true` | Close the WebSocket when the HTTP session it was opened in ends |
| `sessionAccess` | boolean | `false` | Let inbound WebSocket messages refresh the HTTP session, keeping it alive |
| `sessionAccessThrottleMs` | number | `60000` | Minimum interval, in milliseconds, between session refreshes when `sessionAccess` is enabled |

```typescript
// Keep the session alive while the client is active, close the socket on logout
exports.GET = (req) => {

  if (!req.webSocket) {
    return { status: 404 };
  }

  return {
    webSocket: {
      subProtocols: ['text'],
      terminateOnSessionExit: true,   // close the socket when the session ends (default)
      sessionAccess: true,            // inbound messages keep the session alive
      sessionAccessThrottleMs: 30000  // refresh the session at most every 30 seconds
    }
  };
};
```

### Closing on session end

By default, a WebSocket opened within an HTTP session is closed when that session ends — whether through explicit logout (invalidation) or idle-timeout expiry. The socket is closed with code `1008` (policy violation) and reason `HTTP session ended`; the implementation receives the usual `close` event with `closeReason` `1008`. Set `terminateOnSessionExit: false` to let the socket outlive its session.

If the upgrade request carries no HTTP session, there is nothing to bind, and the socket stays open regardless of this parameter.

> **Note:** Idle-expired sessions are invalidated by a periodic sweep, not at the exact moment the timeout elapses, so the close can lag the configured session timeout slightly. The sweep runs at one tenth of the session timeout, clamped between 10 seconds and 10 minutes.

### Keeping the session alive

A user who only interacts through an open WebSocket generates no HTTP requests, so their session can idle out — and, with the default `terminateOnSessionExit`, take the socket down with it. Set `sessionAccess: true` to count inbound messages (client to server) as session activity: each message refreshes the session the socket was opened in. Messages pushed from the server to the client never count as activity.

Refreshes are throttled to at most one per `sessionAccessThrottleMs` milliseconds (default `60000`); messages arriving within the throttle window are delivered normally but do not touch the session. `sessionAccess` works independently of `terminateOnSessionExit` — it refreshes the session even for a socket configured to outlive it.
