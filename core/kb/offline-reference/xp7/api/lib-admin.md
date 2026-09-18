<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-admin generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-admin.md

# Admin API

This API provides admin-related functions.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-admin:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import adminLib from '/lib/xp/admin';
```

## Functions

### getAssetsUri

Returns the admin assets uri.

Parameters

None

Returns

**string** : A URI pointing to the admin assets

### getBaseUri

Returns the admin base uri.

Parameters

None

Returns

**string** : The admin base URI

### getHomeToolUrl

Returns the URL for the Home admin tool.

Parameters

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| type | string | Either `server` (server-relative URL) or `absolute` |

Returns

**string** : The URL pointing to the Home Tool

### getInstallation

Returns installation name.

Parameters

None

Returns

**string** : The installation name

### getLauncherPath

Returns URL to JS script for embedding XP Launcher panel.

Parameters

None

Returns

**string** : URL of the Launcher JS script

### getLauncherUrl

Returns URL of the Launcher panel.

Parameters

None

Returns

**string** : URL of the Launcher panel

### getLocale

Returns the preferred locale based on current HTTP request, or the default server locale if none is specified.

Parameters

None

Returns

**string** : The preferred locale for this request

### getLocales

Returns the list of preferred locales based on current HTTP request, or the default server locale if none is specified.

Parameters

None

Returns

**string[]** : Current locales in order of preference

### getPhrases

Returns all i18n phrases.

Parameters

None

Returns

**object** : JSON object with phrases

### getToolUrl

Returns URL of an admin tool in an application.

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| application | string | Full application name (f.ex, 'com.enonic.app') |
| tool | string | Name of the tool inside an app (f.ex, 'main') |

Returns

**string** : URL of the requested admin tool.

### getVersion

Returns version of XP installation.

Parameters

None

Returns

**string** : The version number of the XP runtime.
