<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-app generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-app.md

# Application API

XP 7.11.0 API for fetching and manipulating applications.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-app:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import appLib from '/lib/xp/app';
```

## Functions

### get

Returns an installed application. If a local and a virtual app are both installed with the specified key, then the local one will take precedence and will be returned in the result.

Parameters

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| params | object | JSON with parameters      Properties                Name | Type | Description |
| key | string | Application key |  |  |

Returns

**object** : ([`Application`](#application)) Property object of an installed application with the specified key, or `null` if the application was not found.

Example

Fetches an application:

```typescript
import {get as getApp} from '/lib/xp/app';

const application = getApp({key: 'my-app-key'});

if (application) {
  log.info('Application name = %s', application.displayName);
} else {
  log.info('Application not found');
}
```

Return value:

```typescript
const expected = {
    key: 'my-app',
    displayName: 'app display name',
    vendorName: 'vendor name',
    vendorUrl: 'https://vendor.url',
    url: 'https://myapp.url',
    version: '1.0.0',
    systemVersion: '4.2.3-SNAPSHOT',
    minSystemVersion: '2.0.0',
    maxSystemVersion: '3.0.0',
    modifiedTime: '2020-09-25T10:00:00Z',
    started: true,
    system: false
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
        displayName: 'app display name',
        vendorName: 'vendor name',
        vendorUrl: 'https://vendor.url',
        url: 'https://myapp.url',
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
        displayName: 'app display name 2',
        vendorName: 'vendor name 2',
        vendorUrl: 'https://vendor2.url',
        url: 'https://myapp2.url',
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

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| params | object | JSON with parameters      Properties                Name | Type | Description |
| key | string | Application key |  |  |

Returns

**object** : ([`ApplicationDescriptor`](#applicationDescriptor)) Application descriptor.

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
    icon: {
        data: {},
        mimeType: 'image/png',
        modifiedTime: '2021-12-03T10:15:30Z'
    }
};
```

### createVirtualApplication

Creates a virtual application (along with its schema repository nodes) with the specified key.

> **Tip:** This function requires the Schema Admin role. It means that user role in the current context may lack sufficient permissions, for example when executed from inside a service - in this case you must explicitly execute the function in the [context](/docs/platform/7.x/api/lib-context#runcontext) of `system.schema.admin` role.

Parameters

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| params | object | JSON with params      Properties                Name | Type | Description |
| key | string | Application key |  |  |

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

> **Tip:** This function requires the Schema Admin role. It means that user role in the current context may lack sufficient permissions, for example when executed from inside a service - in this case you must explicitly execute the function in the [context](/docs/platform/7.x/api/lib-context#runcontext) of `system.schema.admin` role.

Parameters

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| params | object | JSON with params      Properties                Name | Type | Description |
| key | string | Application key |  |  |

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

Parameters

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| params | object | JSON with params      Properties                Name | Type | Description |
| key | string | Application key |  |  |

Returns

**string** : Application mode. Can be one of the following types:

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
| displayName | string | Display name |
| vendorName | string | Vendor name |
| vendorUrl | string | Vendor url |
| url | string | Url |
| version | string | Version |
| systemVersion | string | System version |
| minSystemVersion | string | Min system version |
| maxSystemVersion | string | Max system version |
| modifiedTime | object | Modified time |
| started | boolean | `true` if the application is started. Virtual applications are always started |
| system | boolean | `true` for a system application |

### ApplicationDescriptor

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| key | string | Application key |
| description | `string | Application description |
| icon | [Icon](#icon) | Application icon |

### Icon

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| data | object | icon stream data |
| mimeType | string | icon mime type |
| modifiedTime | string | icon modified time |
