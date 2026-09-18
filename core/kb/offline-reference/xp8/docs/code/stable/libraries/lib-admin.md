<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-admin generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-admin.md

# Admin library

This API provides admin-related functions.

## Usage

```groovy
dependencies {
  include xplibs.admin
}
```

```typescript
import adminLib from '/lib/xp/admin';
```

## Functions

### getInstallation

Returns the installation name.

Parameters

None

Returns

**string** : The installation name.

Example

```typescript
import {getInstallation} from '/lib/xp/admin';

const name = getInstallation();
```

### getVersion

Returns the version of the XP installation.

Parameters

None

Returns

**string** : The version number of the XP runtime.

Example

```typescript
import {getVersion} from '/lib/xp/admin';

const version = getVersion();
```

### getToolUrl

Returns the URL for an admin tool of a specific application.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| application | string | Full application name (f.ex, `com.enonic.app.main`). |
| tool | string | Name of the tool inside an app (f.ex, `main`). |

Returns

**string** : URL of the requested admin tool.

Example

```typescript
import {getToolUrl} from '/lib/xp/admin';

const url = getToolUrl('com.enonic.app.main', 'main');
```

### getHomeToolUrl

Returns the URL for the Home admin tool.

Parameters

`getHomeToolUrl()` takes a single, optional `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |

Returns

**string** : The URL pointing to the Home admin tool.

Example

```typescript
import {getHomeToolUrl} from '/lib/xp/admin';

const url = getHomeToolUrl({type: 'absolute'});
```

### extensionUrl

Returns the URL for an admin extension.

Parameters

`extensionUrl()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Application key that provides the extension. |
| extension | string | Name of the extension. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

Returns

**string** : URL of the requested extension.

Example

```typescript
import {extensionUrl} from '/lib/xp/admin';

const url = extensionUrl({
    application: 'com.enonic.app.main',
    extension: 'launcher',
    type: 'absolute',
    params: {
        id: '42'
    }
});
```

### widgetUrl

> **Warning:** Deprecated — use [`extensionUrl`](#extensionurl) instead. This function will be removed in future versions.

Returns the URL for a widget. Equivalent to calling `extensionUrl` with `extension` set to the widget name.

Parameters

`widgetUrl()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| application | string | Application key that provides the widget. |
| widget | string | Name of the widget. |
| type | string | **Optional.** URL type. Either `server` (server-relative URL) or `absolute`. Default is `server`. |
| params | object | **Optional.** Custom query parameters to append to the URL. |

Returns

**string** : URL of the requested widget.
