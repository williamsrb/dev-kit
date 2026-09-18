<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-websocket generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-websocket.md

# Websocket library

Websocket functions.

## Usage

```groovy
dependencies {
  include xplibs.websocket
}
```

```typescript
import webSocketLib from '/lib/xp/websocket';
```

## Functions

### addToGroup

Adds an id to a socket group.

Takes two positional arguments: `group` (string — group name) and `id` (string — socket id).

Returns

**void**

Example

```typescript
import {addToGroup} from '/lib/xp/websocket';

addToGroup('people', session.id);
```

### removeFromGroup

Removes an id from a socket group.

Takes two positional arguments: `group` (string — group name) and `id` (string — socket id).

Returns

**void**

Example

```typescript
import {removeFromGroup} from '/lib/xp/websocket';

removeFromGroup('people', session.id);
```

### send

Sends a message directly to a socket id.

Takes two positional arguments: `id` (string — socket id) and `message` (string — text message).

Returns

**void**

Example

```typescript
import {send} from '/lib/xp/websocket';

send(session.id, 'You said - ' + message);
```

### sendToGroup

Sends a message to all sockets in group.

Takes two positional arguments: `group` (string — group name) and `message` (string — text message).

Returns

**void**

Example

```typescript
import {sendToGroup} from '/lib/xp/websocket';

sendToGroup('people', 'Notice this message!');
```

### getGroupSize

Gets number of all sockets in a group.

> **Note:** Calculating size of a group has a linear cost from total number of sockets. Consider using this method only if building a message is a resource consuming operation, otherwise it is better to simply `sendToGroup`.

Takes one positional argument: `group` (string — group name).

Returns

**number**

Example

```typescript
import {getGroupSize} from '/lib/xp/websocket';

getGroupSize('people');
```
