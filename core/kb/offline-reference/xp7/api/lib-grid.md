<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-grid generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-grid.md

# Grid API

XP 7.10.0 This API provides functions that enable sharing data across all applications and cluster nodes.

> **Note:** Due to distributed nature of `SharedMap` not all value types can be used. Strings, numbers, and pure JSON objects are supported. There is no runtime check for type compatibility due to performance reasons. Developers are themselves responsible for NOT modifying shared objects (keys and values) in place.

## Usage

Add the following dependency to your `build.gradle` file:

```groovy
dependencies {
  include "com.enonic.xp:lib-grid:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import gridLib from '/lib/xp/grid';
```

## Functions

### getMap

This function returns an instance of `SharedMap` for the specified map identifier.

Parameters

| Name | Kind | Description |
| --- | --- | --- |
| key | string | map identifier |

Returns

**SharedMap** : JS object.

```typescript
import {getMap} from '/lib/xp/grid';

const sharedMap = getMap('mapId');
```

## SharedMap API

### set

Puts an entry into a SharedMap with a given time to live (TTL).

Parameters

| Name | Kind | Description |
| --- | --- | --- |
| key | string | Key of the entry |
| value | string\|number\|boolean\|JSON\|null | Value of the entry |
| ttlSeconds | number | Maximum time (in seconds) for this entry to remain in the map. 0 means infinite, a negative value means default TTL setting of the map provider (for instance, Hazelcast) or infinite if map provider doesn’t have own TTL setting. |

```typescript
import gridLib from '/lib/xp/grid';

const sharedMap = gridLib.getMap('mapId');

sharedMap.set({
  key: 'key',
  value: 'value',
  ttlSeconds: 2 * 60 * 1000
});
```

### get

Returns a value to which the specified key is mapped, or `null` if this map contains no mapping for the key.

Parameters

| Name | Kind | Description |
| --- | --- | --- |
| key | string | The key for a value to be returned |

```typescript
import gridLib from '/lib/xp/grid';

const sharedMap = gridLib.getMap('mapId');

const value = sharedMap.get('key');
```

### delete

Removes entry for the specified key if it is present in the map.

Parameters

| Name | Kind | Description |
| --- | --- | --- |
| key | string | The key for a value to be removed |

```typescript
import gridLib from '/lib/xp/grid';

const sharedMap = gridLib.getMap('mapId');

sharedMap.delete('key');
```

### modify

Attempts to compute a mapping for the specified key and its current mapped value.

Parameters

| Name | Kind | Description |
| --- | --- | --- |
| key | string | Key of the entry. |
| func | function | Mapping function that accepts the existing mapped value (or null, if there is no associated mapping). A value returned by the function will replace the existing mapped value for the specified key. If the returned value is null then the entry will be removed from the map. |
| ttlSeconds | number | Maximum time (in seconds) for this entry to remain in the map. 0 means infinite, a negative value means default TTL setting of the map provider (for instance, Hazelcast) or infinite if map provider doesn’t have own TTL setting. |

```typescript
import gridLib from '/lib/xp/grid';

const sharedMap = gridLib.getMap('mapId');

let newValue = sharedMap.modify({
  key: 'key',
  func: (oldValue) =>{
      return oldValue + 1;
  },
  ttlSeconds: 2 * 60 * 1000
});
```
