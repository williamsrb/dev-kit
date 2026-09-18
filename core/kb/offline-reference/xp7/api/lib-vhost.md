<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-vhost generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-vhost.md

# Virtual Host API

XP 7.6.0

This API provides functions for retrieving information about existing virtual host mappings.

## Usage

Add the following dependency to your `build.gradle` file:

```groovy
dependencies {
  include "com.enonic.xp:lib-vhost:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import vhostLib from '/lib/xp/vhost';
```

## Functions

### isEnabled

Returns value which is set for the `enabled` property in the `com.enonic.xp.web.vhost.cfg` file.

Returns

**Boolean** : Returns `true` if vhost mapping is enabled, otherwise `false`.

Example

```typescript
import vhostLib from '/lib/xp/vhost';

const isEnabled = vhostLib.isEnabled();
```

### list

Returns list of vhost mappings which are specified in the `com.enonic.xp.web.vhost.cfg` file.

Returns

**Object** : Returns an object with `vhosts` array.

Example

```typescript
import vhostLib from '/lib/xp/vhost';

const vhostMappings = vhostLib.list();

const vhosts = vhostMappings.vhosts;
```

For instance, if the `com.enonic.xp.web.vhost.cfg` file contains the following mapping:

```properties
mapping.admin.host = localhost
mapping.admin.source = /admin
mapping.admin.target = /admin
mapping.admin.idProvider.system = default

mapping.admintool.host = localhost
mapping.admintool.source = /admin
mapping.admintool.target = /admin
mapping.admintool.idProvider.system = default
```

Sample response

```typescript
const expected = {
  vhosts: [
    {
      name: "admin",
      source: "/admin",
      target: "/admin",
      host: "localhost",
      defaultIdProviderKey: "system",
      idProviderKeys: [
        {
          idProviderKey: "system"
        }
      ]
    },
    {
      name: "admintool",
      source: "/admin",
      target: "/admin",
      host: "localhost",
      defaultIdProviderKey: "system",
      idProviderKeys: [
        {
          idProviderKey: "system"
        }
      ]
    }
  ]
}
```
