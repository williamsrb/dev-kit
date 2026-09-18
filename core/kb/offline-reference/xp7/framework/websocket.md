<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/websocket generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/websocket.md

# HTTP WebSockets

HTTP WebSockets enable two-way communication with HTTP clients

## Websockets

Websocket support allows a service to act as a websocket channel that you can connect to from a web-browser.

A `get` method must be implemented to handle initialization of the websocket. It can supply `data` object that will be available via `event.data`.

```javascript
// Create a websocket if websocket request.
exports.get = function (req) {

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
    // Do something on message recieved
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
| ****5** | Authenticated user data when WebSocket was opened, if available. XP 7.6.0 |
| ****6** | Data returned from WebSocket `get` controller. |
| ****7** | Error message, if available. |
| ****8** | WebSocket Close reason code, if available. |
| ****9** | WebSocket message, if available. |

Below is an example of a simple chat using the [Websocket JS api](/docs/platform/7.x/api/lib-websocket) for sending messages back and adding/removing clients in groups. Adding to groups allows for multicast message sending.

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
    // Propegate message to group
    webSocketLib.sendToGroup('chat', event.message);
  }

  if (event.type == 'close') {
    log.info(`User left the chat`);
  }

};
```
