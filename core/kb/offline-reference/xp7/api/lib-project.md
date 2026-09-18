<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-project generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-project.md

# Content Project API

XP 7.3.0

This API provides functions for management of Content Projects.

## Usage

Add the following dependency to your `build.gradle` file:

```groovy
dependencies {
  include "com.enonic.xp:lib-project:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import projectLib from '/lib/xp/project';
```

## Functions

### addPermissions

Adds permissions to an existing Content Project.

> **Note:** To modify permissions, user must have `Owner` permissions for the project, or either `system.admin` or `cms.admin` role.

> **Tip:** You can read about project permissions in the dedicated [Content Projects](https://developer.enonic.com/docs/content-studio/stable/projects#roles) section

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| id | string | Unique project id to identify the project. |
| permissions | Object.<string, string[]> | Project permissions to add. 1 to 5 properties where key is role id and value is an array of principals. |

Returns

**Object** : All current project permissions.

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
  id: 'my-project',
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

Parameters

| Name | Type | Attributes | Description |  |  |
| --- | --- | --- | --- | --- | --- |
| id | string |  | Unique project id (alphanumeric characters and hyphens allowed). |  |  |
| displayName | string |  | Project display name. |  |  |
| parent | string | <optional> | XP 7.6.0 Parent project id. If provided, the new project will be a Content Layer that automatically inherits changes from the parent project. |  |  |
| description | string | <optional> | Project description. |  |  |
| language | string | <optional> | Default project language. |  |  |
| siteConfig | Object.<string, Object>[] | <optional> | Applications (with optional configurations) to be assigned to the project                      Name | Type | Description |
| applicationKey | string | Application key |  |  |  |
| config | Object | Application config json |  |  |  |

permissions

Object.

Project permissions. 1 to 5 properties where key is role id and value is an array of principals.

| Name | Type | Description |
| --- | --- | --- |
| role | string | Role id (one of `owner`, `editor`, `author`, `contributor`, `viewer`). |
| principals | string[] | Array of principals. |

readAccess

Object.

Read access settings.

| Name | Type | Description |
| --- | --- | --- |
| public | boolean | Public read access (READ permissions for `system.everyone`). |

Returns

**Object** : Project object.

Example

Create a Content Project with minimal properties

```typescript
import {create} from '/lib/xp/project';

try {
    const project = create({
        id: 'my-project',
        displayName: 'My Content Project',
        readAccess: {
            public: true
        }
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
  permissions: [],
  readAccess: {
    public: true
  }
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
    readAccess: {
        public: false
    }
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
  readAccess: {
    public: false
  }
}
```

### delete

Deletes an existing Content Project and the project repository along with all the data inside.

> **Note:** To delete a project, user must have either `system.admin` or `cms.admin` role.

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| id | string | Unique project id to identify the project. |

Returns

**boolean** : `true` if the project is successfully deleted.

Example

Delete an existing content project

```typescript
import {delete as deleteProject} from '/lib/xp/project';

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

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| id | string | Unique project id to identify the project. |

Returns

**Object** : Content Project object or `null` if not found.

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

Returns

**Object[]** : Array of Content Project objects.

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
    description: 'Default project'
},
{
    id: 'my-project',
    displayName: 'My Content Project',
    permissions: [],
    readAccess: {
        public: true
    }
}]
```

### modify

Modifies an existing Content Project.

> **Note:** To modify a project, user must have `Owner` permissions for this project, or either `system.admin` or `cms.admin` role.

Parameters

| Name | Type | Attributes | Description |  |  |
| --- | --- | --- | --- | --- | --- |
| id | string |  | Unique project id (alpha-numeric characters and hyphens allowed). |  |  |
| displayName | string | <optional> | Project display name. |  |  |
| description | string | <optional> | Project description. |  |  |
| language | string | <optional> | Default project language. |  |  |
| siteConfig | Object.<string, Object>[] | <optional> | Applications (with optional configurations) to be assigned to the project.                      Name | Type | Description |
| applicationKey | string | Application key |  |  |  |
| config | Object | Application config json |  |  |  |

Returns

**Object** : Modified project object.

Example

Modify an existing content project

```typescript
import {modify} from '/lib/xp/project';

const project = modify({
    id: 'my-project',
    displayName: 'New project name',
    description: 'New project description',
    language: 'en',
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
    readAccess: {
        public: true
    }
}
```

### modifyReadAccess

Toggles public/private READ access for an existing Content Project. This will modify permissions on ALL the content items inside the project repository by adding or removing READ access for `system.everyone`.

> **Note:** To modify READ access, user must have `Owner` permissions for the project, or either `system.admin` or `cms.admin` role.

Parameters

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| id | string | Unique project id (alpha-numeric characters and hyphens allowed). |  |  |
| readAccess | Object.<string, boolean> | Read access settings.                      Name | Type | Description |
| public | boolean | Public read access (READ permissions for `system.everyone`). |  |  |

Returns

**Object** : Current state of public READ access.

Example

Set content project as not available for public READ access

```typescript
import {addPermissions} from '/lib/xp/project';

const currentPermissions = addPermissions({
    id: 'my-project',
    readAccess: {
        public: false
    }
});
```

Sample response

```typescript
const expected = {
    id: 'my-project',
    readAccess: {
        public: false
    }
}
```

### removePermissions

Removes permissions from an existing Content Project.

> **Note:** To remove permissions, user must have `Owner` permissions for the project, or either `system.admin` or `cms.admin` role.

Parameters

| Name | Type | Description |  |  |
| --- | --- | --- | --- | --- |
| id | string | Unique project id (alpha-numeric characters and hyphens allowed). |  |  |
| permissions | Object.<string, string[]> | Project permissions to delete. 1 to 5 properties where key is role id and value is an array of principals.                      Name | Type | Description |
| role | string | Role id (one of `owner`, `editor`, `author`, `contributor`, `viewer`). |  |  |
| principals | string[] | Array of principals to delete from this project role. |  |  |

Returns

**Object** : All current project permissions.

Adds and then removes permissions from an existing content project

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
    id: 'my-project',
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

XP 7.11.0

Returns available applications of a specified project. The result contains active apps assigned to the project and all of its parents, if any.

Parameters

| Name | Kind | Details |
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
