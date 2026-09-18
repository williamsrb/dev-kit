<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-vhost generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-vhost.md

# Virtual Host library

This API provides functions for retrieving information about existing virtual host mappings.

## Usage

Add the following dependency to your `build.gradle` file:

```groovy
dependencies {
  include xplibs.vhost
}
```

```typescript
import vhostLib from '/lib/xp/vhost';
```

## Functions

### isEnabled

Returns the value of the `enabled` property in the `com.enonic.xp.web.vhost.cfg` file.

`isEnabled()` takes no arguments.

Returns

**boolean** : `true` if vhost mapping is enabled, otherwise `false`.

Example

```typescript
import {isEnabled} from '/lib/xp/vhost';

const enabled = isEnabled();
```

### list

Returns the virtual host mappings configured in `com.enonic.xp.web.vhost.cfg`.

`list()` takes no arguments.

Returns

**object** : ([`VirtualHosts`](#virtual-hosts)) Object with a `vhosts` array. The array is empty when no mappings are configured.

Example

```typescript
import {list} from '/lib/xp/vhost';

const {vhosts} = list();
```

For instance, given the following `com.enonic.xp.web.vhost.cfg`:

```properties
mapping.admin.host = localhost
mapping.admin.source = /
mapping.admin.target = /admin
mapping.admin.idProvider.system = default

mapping.api.host = api.localhost
mapping.api.source = /
mapping.api.target = /api
mapping.api.idProvider.system = default
```

Sample response

```typescript
const expected = {
  vhosts: [
    {
      name: 'admin',
      source: '/',
      target: '/admin',
      host: 'localhost',
      defaultIdProviderKey: 'system',
      idProviderKeys: [
        {idProviderKey: 'system'}
      ]
    },
    {
      name: 'api',
      source: '/',
      target: '/api',
      host: 'api.localhost',
      defaultIdProviderKey: 'system',
      idProviderKeys: [
        {idProviderKey: 'system'}
      ]
    }
  ]
};
```

## Type Definitions

### VirtualHosts

Properties

| Name | Type | Description |
| --- | --- | --- |
| vhosts | [`VirtualHost[]`](#virtual-host) | All configured virtual host mappings. Empty when none are configured. |

### VirtualHost

Properties

| Name | Type | Description |
| --- | --- | --- |
| name | string | Mapping name (the suffix used in `mapping.<name>.*` config keys). |
| source | string | Source path that the mapping matches. |
| target | string | Target path that the mapping rewrites to. |
| host | string | Host name that the mapping matches. |
| `defaultIdProviderKey` | string | **Optional.** Key of the default ID provider, when configured. |
| `idProviderKeys` | [`IdProviderKey[]`](#id-provider-key) | **Optional.** ID providers attached to the mapping. |

### IdProviderKey

Properties

| Name | Type | Description |
| --- | --- | --- |
| `idProviderKey` | string | ID provider key. |
