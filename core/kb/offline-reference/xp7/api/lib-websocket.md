<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-websocket generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-websocket.md

# Websocket API

Websocket functions.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-websocket:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import webSocketLib from '/lib/xp/websocket';
```

## Functions

### addToGroup

Adds an id to a socket group.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| group | string | Group name |
| id | string | Socket id |

Returns

**void**

Example

```typescript
import {addToGroup} from '/lib/xp/websocket';

addToGroup('people', session.id);
```

### removeFromGroup

Removes an id from a socket group.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| group | string | Group name |
| id | string | Socket id |

Returns

**void**

Example

```typescript
import {removeFromGroup} from '/lib/xp/websocket';

removeFromGroup('people', session.id);
```

### send

Sends a message directly to a socket id.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| id | string | Socket id |
| message | string | Text message |

Returns

**void**

Example

```typescript
import {send} from '/lib/xp/websocket';

send(session.id, 'You said - ' + message);
```

### sendToGroup

Sends a message to all sockets in group.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| group | string | Group name |
| message | string | Text message |

Returns

**void**

Example

```typescript
import {sendToGroup} from '/lib/xp/websocket';

sendToGroup('people', 'Notice this message!');
```

### getGroupSize

XP 7.6.0 Gets number of all sockets in a group.

> **Note:** Calculating size of a group has a linear cost from total number of sockets. Consider using this method only if building a message is a resource consuming operation, otherwise it is better to simply `sendToGroup`.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| group | string | Group name |

Returns

**number**

Example

```typescript
import {getGroupSize} from '/lib/xp/websocket';

getGroupSize('people');
```
