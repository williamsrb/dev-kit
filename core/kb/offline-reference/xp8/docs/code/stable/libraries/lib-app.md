<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-app generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-app.md

# Application library

API for fetching and manipulating applications.

## Usage

```groovy
dependencies {
  include xplibs.app
}
```

```typescript
import appLib from '/lib/xp/app';
```

## Functions

### get

Returns an installed application. If a local and a virtual app are both installed with the specified key, then the local one will take precedence and will be returned in the result.

Parameters

`get()` takes a single `GetApplicationParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Application key. |

Returns

**object** : ([`Application`](#application)) Property object of an installed application with the specified key, or `null` if the application was not found.

Example

Fetches an application:

```typescript
import {get as getApp} from '/lib/xp/app';

const application = getApp({key: 'my-app-key'});

if (application) {
  log.info('Application key = %s', application.key);
} else {
  log.info('Application not found');
}
```

Return value:

```typescript
const expected = {
    key: 'my-app',
    version: '1.0.0',
    systemVersion: '4.2.3-SNAPSHOT',
    minSystemVersion: '2.0.0',
    maxSystemVersion: '3.0.0',
    modifiedTime: '2020-09-25T10:00:00Z',
    started: true,
    system: true
};
```

### list

Fetches all installed applications. If a local and a virtual app are both installed with the same key, then the local one will take precedence and will be returned in the result.

Returns

**object[]** : ([`Application[]`](#application)) Array of applications' property objects, or an empty array if there are no installed applications.

Example

Fetching all applications:

```typescript
import {list} from '/lib/xp/app';
const apps = list();
```

Return value:

```typescript
const expected = [
    {
        key: 'app1',
        version: '1.0.0',
        systemVersion: '1.21.3',
        minSystemVersion: '2.0.0',
        maxSystemVersion: '3.0.0',
        modifiedTime: '2020-09-25T10:00:00Z',
        started: true,
        system: false
    },
    {
        key: 'app2',
        version: '4.1.2',
        systemVersion: '1.2.33-SNAPSHOT',
        minSystemVersion: '5.3.11',
        maxSystemVersion: '3.0.6',
        modifiedTime: '2021-09-25T10:00:00Z',
        started: false,
        system: true
    }
];
```

### getDescriptor

Returns descriptor of an installed application.

Parameters

`getDescriptor()` takes a single `GetApplicationDescriptorParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Application key. |

Returns

**object** : ([`ApplicationDescriptor`](#applicationDescriptor)) Application descriptor, or `null` if the application was not found.

Example

Fetches application descriptor:

```typescript
import {getDescriptor} from '/lib/xp/app';
const descriptor = getDescriptor({key: 'my-app-key'});
```

Return value:

```typescript
const expected = {
    key: 'my-app',
    description: 'my app description',
    descriptionI18nKey: 'myapp.description',
    title: 'My app',
    titleI18nKey: 'myapp.title',
    vendorName: 'vendor name',
    vendorUrl: 'https://vendor.url',
    url: 'https://myapp.url',
    icon: {
        data: {},
        mimeType: 'image/png',
        modifiedTime: '2021-12-03T10:15:30Z'
    }
};
```

### createVirtualApplication

Creates a virtual application (along with its schema repository nodes) with the specified key.

> **Tip:** This function requires the Schema Admin role. It means that user role in the current context may lack sufficient permissions, for example when executed from inside a service - in this case you must explicitly execute the function in the [context](docs/code/stable/libraries/lib-context.md#runcontext) of `system.schema.admin` role.

Parameters

`createVirtualApplication()` takes a single `CreateVirtualApplicationParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Application key. |

Returns

**object** : ([`Application`](#application)) Property object of the created application.

Example

creates an app with my-app-key key:

```typescript
import {createVirtualApplication} from '/lib/xp/app';

const app = createVirtualApplication({
    key:'my-app-key'
});
```

### deleteVirtualApplication

Removes a virtual application with the specified key.

> **Tip:** This function requires the Schema Admin role. It means that user role in the current context may lack sufficient permissions, for example when executed from inside a service - in this case you must explicitly execute the function in the [context](docs/code/stable/libraries/lib-context.md#runcontext) of `system.schema.admin` role.

Parameters

`deleteVirtualApplication()` takes a single `DeleteVirtualApplicationParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Application key. |

Returns

**boolean** : `true` if deletion succeeded, otherwise `false`.

Example

removes an app with my-app-key key:

```typescript
import {deleteVirtualApplication} from '/lib/xp/app';

const result = deleteVirtualApplication({
    key:'my-app-key'
});
```

### getApplicationMode

Fetches mode of an application with the specified key.

> **Tip:** This function requires the Schema Admin role. It means that user role in the current context may lack sufficient permissions, for example when executed from inside a service - in this case you must explicitly execute the function in the [context](docs/code/stable/libraries/lib-context.md#runcontext) of `system.schema.admin` role.

Parameters

`getApplicationMode()` takes a single `GetApplicationModeParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Application key. |

Returns

**string** : Application mode, or `null` if the application is not installed (neither as a bundled app nor as a virtual app). When the application is installed, the value is one of:

- `bundled` - an installed and active application, no virtual app with the same key exists;

- `virtual` - a "virtual", node-based application, no bundled app with the same key exists;

- `augmented` - both bundled and virtual application co-exist with the same application key.

> **Note:** Installed but disabled bundled applications are considered missing.

Example

fetches mode of an application with my-app-key key:

```typescript
import {getApplicationMode} from '/lib/xp/app';
const result = getApplicationMode({
    key:'my-app-key'
});
```

## Type Definitions

### Application

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| key | string | Application key |
| version | string | Application version. May be `null` |
| systemVersion | string | XP version the application was built against. May be `null` |
| minSystemVersion | string | Minimum XP version required to run the application. May be `null` |
| maxSystemVersion | string | Maximum XP version supported by the application. May be `null` |
| modifiedTime | string | Last modification time, ISO-8601 instant. May be `null` |
| started | boolean | `true` if the application is started. Virtual applications are always started |
| system | boolean | `true` for a system application |

### ApplicationDescriptor

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| key | string | Application key |
| description | string | Application description |
| descriptionI18nKey | string | i18n key for the application description. May be `null` |
| title | string | Application title. May be `null` |
| titleI18nKey | string | i18n key for the application title. May be `null` |
| vendorName | string | Vendor name. May be `null` |
| vendorUrl | string | Vendor URL. May be `null` |
| url | string | Application URL. May be `null` |
| icon | [Icon](#icon) | Application icon. Omitted when the application has no icon |

### Icon

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| data | [ByteSource](docs/code/stable/fundamentals/types.md#byte-source) | Icon binary data, as a stream that can be read with `lib-io` |
| mimeType | string | Icon MIME type |
| modifiedTime | string | Icon modified time, ISO-8601 instant |
