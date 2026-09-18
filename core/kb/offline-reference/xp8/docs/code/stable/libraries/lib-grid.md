<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-grid generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-grid.md

# Grid library

This API provides functions that enable sharing data across all applications and cluster nodes.

> **Note:** Due to distributed nature of `SharedMap` not all value types can be used. Strings, numbers, booleans, and pure JSON objects are supported. There is no runtime check for type compatibility due to performance reasons. Developers are themselves responsible for NOT modifying shared objects (keys and values) in place.

## Usage

Add the following dependency to your `build.gradle` file:

```groovy
dependencies {
  include xplibs.grid
}
```

```typescript
import gridLib from '/lib/xp/grid';
```

## Functions

### getMap

This function returns an instance of `SharedMap` for the specified map identifier.

Parameters

`getMap()` takes a single positional argument: `mapId` (string) — the map identifier.

Returns

**[SharedMap](#shared-map)** : An instance of `SharedMap` bound to the given identifier.

```typescript
import {getMap} from '/lib/xp/grid';

const sharedMap = getMap('mapId');
```

## SharedMap API

### set

Puts an entry into a SharedMap with a given time to live (TTL). If `value` is `null`, the existing entry for that key is removed.

Parameters

`set()` takes a single `SetParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Key of the entry. |
| value | [SharedMapValueType](#shared-map-value-type) | Value of the entry. Passing `null` removes the existing entry. |
| ttlSeconds | number | **Optional.** Maximum time (in seconds) for this entry to remain in the map. `0` means infinite; a negative value means the default TTL of the map provider (for instance, Hazelcast) or infinite if the provider has no own TTL setting. |

```typescript
import gridLib from '/lib/xp/grid';

const sharedMap = gridLib.getMap<{ greeting: string }>('mapId');

sharedMap.set({
  key: 'greeting',
  value: 'hello',
  ttlSeconds: 2 * 60
});
```

### get

Returns the value to which the specified key is mapped, or `null` if the map contains no mapping for the key.

Parameters

`get()` takes a single positional argument: `key` (string) — the key whose associated value is to be returned.

Returns

**[SharedMapValueType](#shared-map-value-type)** : The value mapped to the given key, or `null` if no mapping exists.

```typescript
import gridLib from '/lib/xp/grid';

const sharedMap = gridLib.getMap('mapId');

const value = sharedMap.get('key');
```

### delete

Removes the entry for the specified key if it is present in the map.

Parameters

`delete()` takes a single positional argument: `key` (string) — the key whose associated entry is to be removed.

```typescript
import gridLib from '/lib/xp/grid';

const sharedMap = gridLib.getMap('mapId');

sharedMap.delete('key');
```

### modify

Attempts to compute a mapping for the specified key and its current mapped value.

Parameters

`modify()` takes a single `ModifyParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Key of the entry. |
| func | function | Mapping function that accepts the existing mapped value (or `null`, if there is no associated mapping). The value it returns replaces the existing mapped value for the specified key. If the returned value is `null`, the entry is removed from the map. |
| ttlSeconds | number | **Optional.** Maximum time (in seconds) for this entry to remain in the map. `0` means infinite; a negative value means the default TTL of the map provider (for instance, Hazelcast) or infinite if the provider has no own TTL setting. |

Returns

**[SharedMapValueType](#shared-map-value-type)** : The new value mapped to the key, or `null` if the entry was removed (because `func` returned `null`).

```typescript
import gridLib from '/lib/xp/grid';

const sharedMap = gridLib.getMap<{ counter: number }>('mapId');

const newValue = sharedMap.modify({
  key: 'counter',
  func: (oldValue) => (oldValue ?? 0) + 1,
  ttlSeconds: 2 * 60
});
```

## Type Definitions

### SharedMap

Type

**interface**

Description

A typed key-value store shared across all applications and cluster nodes. Obtain an instance via `getMap()`. The generic type parameter `Map` constrains which keys and value types are valid for the instance.

Methods: `get()`, `set()`, `delete()`, `modify()` — documented above.

### SharedMapValueType

Type

`string | number | boolean | object | null`

The union of all value types that a `SharedMap` entry may hold.
