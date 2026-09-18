<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-project generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-project.md

# Content Project library

This API provides functions for management of Content Projects.

## Usage

Add the following dependency to your `build.gradle` file:

```groovy
dependencies {
  include xplibs.project
}
```

```typescript
import projectLib from '/lib/xp/project';
```

## Functions

### addPermissions

Adds permissions to an existing Content Project.

> **Note:** To modify permissions, user must have `Owner` permissions for the project, or either `system.admin` or `cms.admin` role.

> **Tip:** You can read about project permissions in the dedicated [Content Projects](https://developer.enonic.com/docs/content-studio/stable/projects#roles) section

`addPermissions()` takes a single `AddProjectPermissionsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Unique project id to identify the project. |
| permissions | [ProjectPermission](#project-permission) | **Optional.** Project permissions to add. Keys are role ids (`owner`, `editor`, `author`, `contributor`, `viewer`); values are arrays of principal keys. |

Returns

**object** : ([`ProjectPermissions`](#project-permissions)) All current project permissions, or `null`.

Example

Add permissions to a project with id 'my-project'

```typescript
import {addPermissions} from '/lib/xp/project';

const currentPermissions = addPermissions({
    id: 'my-project',
    permissions: {
        owner: ['user:mystore:user1', 'user:mystore:user2'],
        editor: ['user:mystore:user3']
    }
});
```

Sample response

```typescript
const expected = {
    permissions: {
        owner: [
            'user:mystore:user1',
            'user:mystore:user2'
        ],
        editor: [
            'user:mystore:user3'
        ]
    }
}
```

### create

Creates a new Content Project.

> **Note:** Only `system.admin` and `cms.admin` roles have permissions to create new projects.

`create()` takes a single `CreateProjectParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Unique project id (alphanumeric characters and hyphens allowed). |
| displayName | string | Project display name. |
| publicRead | boolean | `true` to grant READ permissions to `system.everyone`, `false` otherwise. |
| parents | string[] | **Optional.** Parent project ids. If provided, the new project will be a Content Layer that automatically inherits changes from its parent projects. |
| description | string | **Optional.** Project description. |
| language | string | **Optional.** Default project language. |
| siteConfig | [SiteConfig](#site-config)[] | **Optional.** Applications (with optional configurations) to be assigned to the project. |
| permissions | [ProjectPermission](#project-permission) | **Optional.** Project permissions. Keys are role ids; values are arrays of principal keys. |

Returns

**object** : ([`Project`](#project)) The created project.

Example

Create a Content Project with minimal properties

```typescript
import {create} from '/lib/xp/project';

try {
    const project = create({
        id: 'my-project',
        displayName: 'My Content Project',
        publicRead: true
    });
} catch (e) {
    log.error('Failed to create a project: %s', e.message);
}
```

Sample response

```typescript
const expected = {
  id: 'my-project',
  displayName: 'My Content Project',
  permissions: {},
  publicRead: true
}
```

Create a Content Project with extended properties

```typescript
import {create} from '/lib/xp/project';

const project = create({
    id: 'my-project',
    displayName: 'My Content Project',
    description: 'Some exciting content is stored here',
    language: 'no',
    permissions: {
        owner: ['user:mystore:user1'],
        editor: ['user:mystore:user2'],
        author: ['user:mystore:user3'],
        contributor: ['user:mystore:user4'],
        viewer: ['user:mystore:user5']
    },
    siteConfig: [{
            applicationKey: 'app1',
            config: {
                a: 'b'
            }
        } ,{
            applicationKey: 'app2',
            config: {
                a: true,
                b: 3.4
            }
        }],
    publicRead: false
});
```

Sample response

```typescript
const expected = {
  id: 'my-project',
  displayName: 'My Content Project',
  description: 'Some exciting content is stored here',
  language: 'no',
  siteConfig: [
        {
            applicationKey: 'app1',
            config: {
                a: 'b'
            }
        },
        {
            applicationKey: 'app2',
            config: {
                a: true,
                b: 3.4
            }
        }
    ],
  permissions: {
    owner: [
        'user:mystore:user1'
    ],
    editor: [
        'user:mystore:user2'
    ],
    author: [
        'user:mystore:user3'
    ],
    contributor: [
        'user:mystore:user4'
    ],
    viewer: [
        'user:mystore:user5'
    ]
  },
  publicRead: false
}
```

### deleteProject

Deletes an existing Content Project and the project repository along with all the data inside.

> **Note:** To delete a project, user must have either `system.admin` or `cms.admin` role.

`deleteProject()` takes a single `DeleteProjectParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Unique project id to identify the project. |

Returns

**boolean** : `true` if the project is successfully deleted.

Example

Delete an existing content project

```typescript
import {deleteProject} from '/lib/xp/project';

const result = deleteProject({
    id: 'my-project'
});
```

Sample response

```typescript
const expected = true;
```

### get

Returns an existing Content Project.

> **Note:** To access a project, user must have sufficient permissions for this project, or either `system.admin` or `cms.admin` role.

`get()` takes a single `GetProjectParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Unique project id to identify the project. |

Returns

**object** : ([`Project`](#project)) The project, or `null` if not found.

Example

Fetch an existing content project

```typescript
import {get as getProject} from '/lib/xp/project';

const project = getProject({
    id: 'my-project'
});
```

Sample response

```typescript
const expected = {
    id: 'my-project',
    displayName: 'My Content Project',
    permissions: {
        owner: [
            'user:mystore:user1'
        ],
        editor: [
            'user:mystore:user2'
        ]
    },
    readAccess: {
        public: true
    }
}
```

### list

Returns all Content Projects that user in the current context has permissions for.

> **Note:** Users with `system.admin` or `cms.admin` roles will get the list of all projects.

Takes no arguments.

Returns

**object[]** : ([`Project[]`](#project)) Array of Content Project objects.

Example

Fetch the list of existing content projects

```typescript
import {list} from '/lib/xp/project';

const projects = list();
```

Sample response

```typescript
const expected = [{
    id: 'default',
    displayName: 'Default',
    description: 'Default project',
    permissions: {},
    readAccess: {
        public: true
    }
},
{
    id: 'my-project',
    displayName: 'My Content Project',
    permissions: {},
    readAccess: {
        public: true
    }
}]
```

### modify

Modifies an existing Content Project.

Pass an `editor` function that receives the current project, mutates fields on it, and returns it. Fields the editor doesn’t touch are left unchanged. Setting `description`, `language`, or `siteConfig` to `null` clears them. `displayName` is required and cannot be cleared.

> **Note:** To modify a project, user must have `Owner` permissions for this project, or either `system.admin` or `cms.admin` role.

`modify()` takes a single `ModifyProjectParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Unique project id (alphanumeric characters and hyphens allowed). |
| editor | function | Editor callback that receives the current project (a `Project` merged with `EditableProject`), mutates fields, and returns it. |

Returns

**object** : ([`Project`](#project)) The modified project.

Example

Modify an existing content project

```typescript
import {modify} from '/lib/xp/project';

const project = modify({
    id: 'my-project',
    editor: (project) => {
        project.displayName = 'New project name';
        project.description = 'New project description';
        project.language = 'en';
        project.siteConfig = [{
            applicationKey: 'app1',
            config: { a: 'b' }
        }, {
            applicationKey: 'app2',
            config: { a: true, b: 3.4 }
        }];
        return project;
    }
});
```

Sample response

```typescript
const expected = {
    id: 'my-project',
    displayName: 'New project name',
    description: 'New project description',
    language: 'en',
    siteConfig: [
        {
            applicationKey: 'app1',
            config: {
                a: 'b'
            }
        },
        {
            applicationKey: 'app2',
            config: {
                a: true,
                b: 3.4
            }
        }
    ],
    permissions: {},
    publicRead: true
}
```

### setPublicRead

Toggles public/private READ access for an existing Content Project. This will modify permissions on ALL the content items inside the project repository by adding or removing READ access for `system.everyone`.

> **Note:** To modify READ access, user must have `Owner` permissions for the project, or either `system.admin` or `cms.admin` role.

`setPublicRead()` takes a single `SetProjectPublicReadParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Unique project id (alphanumeric characters and hyphens allowed). |
| publicRead | boolean | `true` to grant READ permissions to `system.everyone`, `false` otherwise. |

Returns

**boolean** : Resulting public-read state.

Example

Set content project as not available for public READ access

```typescript
import {setPublicRead} from '/lib/xp/project';

const publicRead = setPublicRead({
    id: 'my-project',
    publicRead: false
});
```

Sample response

```typescript
const expected = false;
```

### removePermissions

Removes permissions from an existing Content Project.

> **Note:** To remove permissions, user must have `Owner` permissions for the project, or either `system.admin` or `cms.admin` role.

`removePermissions()` takes a single `RemoveProjectPermissionsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Unique project id (alphanumeric characters and hyphens allowed). |
| permissions | [ProjectPermission](#project-permission) | **Optional.** Project permissions to remove. Keys are role ids; values are arrays of principal keys to remove from that role. |

Returns

**object** : ([`ProjectPermissions`](#project-permissions)) All current project permissions after removal, or `null`.

Add and then remove permissions from an existing content project

```typescript
import {addPermissions,removePermissions} from '/lib/xp/project';

addPermissions({
    id: 'my-project',
    permissions: {
        owner: ['user:mystore:user1', 'user:mystore:user2'],
        editor: ['user:mystore:user3']
    }
});

const currentPermissions = removePermissions({
    id: 'my-project',
    permissions: {
        owner: ['user:mystore:user2']
    }
});
```

Sample response

```typescript
const expected = {
    permissions: {
        owner: [
            'user:mystore:user1'
        ],
        editor: [
            'user:mystore:user3'
        ]
    }
}
```

### getAvailableApplications

Returns available applications of a specified project. The result contains active apps assigned to the project and all of its parents, if any.

> **Note:** User must be a member of one of the project roles, or either `system.admin` or `cms.admin` role.

`getAvailableApplications()` takes a single `GetAvailableApplicationsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Unique project id to identify the project. |

Returns

**string[]** : Application keys.

Example

Fetch available applications.

```typescript
import {getAvailableApplications} from '/lib/xp/project';

const project = getAvailableApplications({
    id: 'my-project'
});
```

Sample response

```typescript
const expected = ['app1', 'app2']
```

## Type Definitions

### Project

A Content Project object, as returned by `create()`, `get()`, `list()`, and `modify()`.

Properties

| Name | Type | Description |
| --- | --- | --- |
| id | string | Unique project id. |
| displayName | string | Project display name. |
| publicRead | boolean | Whether all content in the project is publicly readable. |
| parents | string[] | Parent project ids. Empty array when the project is not a Content Layer. |
| description | string | **Optional.** Project description. |
| language | string | **Optional.** Default project language. |
| siteConfig | [SiteConfig](#site-config)[] | **Optional.** Applications assigned to the project, with optional configurations. |
| permissions | [ProjectPermission](#project-permission) | **Optional.** Project role-to-principals mapping. |

### SiteConfig

An application assignment, with optional configuration.

Properties

| Name | Type | Description |
| --- | --- | --- |
| applicationKey | string | Application key. |
| config | object | **Optional.** Application configuration object. |

### ProjectPermission

A partial mapping of project role ids to arrays of principal keys. Keys are one of `owner`, `editor`, `author`, `contributor`, or `viewer`; values are arrays of principal key strings (e.g. `user:mystore:alice`).

### ProjectPermissions

The object returned by `addPermissions()` and `removePermissions()`.

Properties

| Name | Type | Description |
| --- | --- | --- |
| permissions | [ProjectPermission](#project-permission) | Current role-to-principals mapping for the project. |
