<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-auth generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-auth.md

# Auth API

Manage principals and authentication

> **Tip:** If, while using this API, you are getting authentication errors like "*Access denied to user [unknown]*" it means that user role in the current context lacks sufficient permissions (for example when executed from inside a service). In this case you must explicitly execute the function in the [context](/docs/platform/7.x/api/lib-context#runcontext) of System Administrator role.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-auth:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import authLib from '/lib/xp/auth';
```

## Functions

### addMembers

Adds members to a principal (user or role).

Parameters

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Key of the principal to add members to |
| members | string[] |  | A list of the new members that should be added to the principal |

Returns

**void**

### changePassword

Changes password for a specified user.

Parameters

An object with the following keys and their values:

| Name | Attributes | Description |
| --- | --- | --- |
| userKey |  | The key of the user to change password for |
| password |  | The new password |

Returns

**void**

### createGroup

Creates a group.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Description |
| --- | --- | --- | --- |
| idProvider | string |  | Key for id provider where the group will be created |
| name | string |  | Group name |
| displayName | string |  | Group display name |
| description | string |  | A description of the principal |

Returns

**object**: The created group.

Example

Creating a group named "group-a"

```typescript
import {createGroup} from '/lib/xp/auth';

const group = createGroup({
    idProvider: 'myIdProvider',
    name: 'group-a',
    displayName: 'Group A',
    description: "description"
});
```

Sample response

```js
({
    type: "group",
    key: "group:system:group-a",
    displayName: "Group A",
    description: "description"
})
```

### createRole

Creates a role.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Description |
| --- | --- | --- | --- |
| name | string |  | The name of the role. The key of the role will be 'role.<name>'. |
| displayName | string |  | Role display name |
| description | string |  | A description of the role |

Returns

**object**: The created role.

Example

Creating a role named "aRole"

```typescript
import {createRole} from '/lib/xp/auth';

const role = createRole({
    name: 'aRole',
    displayName: 'Role Display Name',
    description: 'description'
});
```

Sample response

```js
({
    type: "role",
    key: "role:aRole",
    displayName: "Role Display Name",
    description: "description"
})
```

### createUser

Creates a user.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Description |
| --- | --- | --- | --- |
| idProvider | string |  | Key for id provider where the user will be created |
| name | string |  | User login name |
| displayName | string |  | User display name |
| email | string | <optional> | Optional user e-mail |

Returns

**object**: The created [`User`](#user).

Example

Creating a user named "userName"

```typescript
import {createUser} from '/lib/xp/auth';

const user = createUser({
    idProvider: 'myIdProvider',
    name: 'user1',
    displayName: 'The One And Only',
    email: 'user1@enonic.com'
});
```

Sample response

```js
({
    type: "user",
    key: "user:system:user1",
    displayName: "The One And Only",
    disabled: false,
    email: "user1@enonic.com",
    login: "user1",
    idProvider: "myIdProvider",
    hasPassword: false
})
```

### deletePrincipal

Deletes the principal with the specified key.

Parameters

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Key of the principal to delete |

Returns

**boolean**: `true` if the principal was deleted, `false` otherwise.

Example

Deleting a user

```typescript
import {deletePrincipal} from '/lib/xp/auth';

const deleted = deletePrincipal('user:myIdProvider:userId');
```

### findPrincipals

Search for principals matching the specified criteria.

An object with the following keys and their value. All parameters are optional:

| Name | Kind | Attributes | Description |
| --- | --- | --- | --- |
| type | string | <optional> | Principal type to look for, one of: 'user', 'group' or 'role'. If not specified all principal types will be included. |
| idProvider | string | <optional> | Key of the id provider to look for. If not specified, all id providers will be included. |
| start | string | <optional> | First principal to return from the search results. It can be used for pagination. |
| count | string | <optional> | A limit on the number of principals to be returned |
| name | string | <optional> | Name of the principal to look for |
| searchText | string | <optional> | Text to look for in any principal field. |

Returns

**object**: The "total" number of principals matching the search, the "count" of principals included, and an array of "hits" containing the principals.

Example

Searching for principals for 'user1'

```typescript
import {findPrincipals} from '/lib/xp/auth';

const result = findPrincipals({
    idProvider: "user-store",
    start: 0,
    count: 10,
    searchText: "user1"
});
```

Sample response

```js
({
    type: "user",
    key: "user:system:user1",
    displayName: "The One And Only",
    disabled: false,
    email: "user1@enonic.com",
    login: "user1",
    idProvider: "myIdProvider",
    hasPassword: true
})
```

### findUsers

Search for users matching the specified query.

An object with the following keys and their values:

| Name | Kind | Attributes | Description |
| --- | --- | --- | --- |
| query | string |  | Query expression |
| start | number | <optional> | Optional start index for paging |
| count | number | <optional> | Optional number of users to fetch at a time |
| sort | string | <optional> | Optional sorting expression |
| includeProfile | boolean | <optional> | If set to `true`, a full profile of each user will be included in the result |

Returns

**object**: An object containing the total number of hits, the number returned and an array of the hits.

Example

Searching for the first person in the Juve family.

```typescript
import {findUsers} from '/lib/xp/auth';

const findUsersResult = findUsers({
    count: 1,
    query: "displayName LIKE '*Juve'"
});
```

Sample response

```js
({
    total: 2,
    count: 1,
    hits: [
        {
            type: "user",
            key: "user:system:jorgen-juve",
            displayName: "Jørgen Juve",
            disabled: false,
            email: "jju@enonic.com",
            login: "jorgen-juve",
            idProvider: "system",
            hasPassword: true
        }
    ]
})
```

> **Note:** If you want to find a user by key, you have to use `_id` field in the `query` parameter.

Find a user by key.

```typescript
import {findUsers} from '/lib/xp/auth';

const findUsersResult = findUsers({
    count: 1,
    query: "_id = 'user:system:jorgen-juve'"
});
```

### generatePassword

Generates a random secure password that may be suggested to a user.

Parameters

None

Returns

**string**: A suggestion for a secure password.

Example

Generate a password and return the password string

```typescript
import {generatePassword} from '/lib/xp/auth';

const pwd = generatePassword();
```

### getIdProviderConfig

This function returns the ID provider configuration. It is meant to be called from an ID provider controller.

Parameters

None

Returns

**object**: An object with all the values in the configuration.

### getMembers

Returns a list of principals that are members of the specified principal.

Parameters

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Principal key to retrieve the members of. |

Returns

**object[]**: A list of objects for each member of the principal or empty array if none.

Example

Searching for members of the Content Manager group

```typescript
import {getMembers} from '/lib/xp/auth';

const result = getMembers('group:system:content-managers');
```

Sample response

```js
[{
    type: "user",
    key: "user:system:user1",
    displayName: "User 1",
    disabled: false,
    email: "user1@enonic.com",
    login: "user1",
    idProvider: "system",
    hasPassword: true
},
{
    type: "user",
    key: "user:system:user2",
    displayName: "User 2",
    disabled: false,
    email: "user2@enonic.com",
    login: "user2",
    idProvider: "system",
    hasPassword: false
}]
```

### getMemberships

Returns the list of principals which the specified principal is a member of.

Parameters

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Principal key to retrieve memberships for |
| transitive | boolean | <optional> | Retrieve transitive memberships. Considered `false` if not specified |

Returns

**string[]**: A list of the principals that the specified principal is a member of.

Example

Searching for direct memberships of 'user1'

```typescript
import {getMemberships} from '/lib/xp/auth';

const result = getMemberships('user:system:user1');
```

Sample response

```js
[{
    type: "role",
    key: "role:system.admin",
    displayName:"Administrator"
}]
```

Searching for transitive memberships of 'user1'

```typescript
import {getMemberships} from '/lib/xp/auth';

const result = getMemberships('user:system:user1', true);
```

Sample response

```js
[
    "role:system.admin.login",
    "group:system:content-managers",
    "role:cms.expert",
    "role:cms.cm.app"
]
```

### getPrincipal

Returns the principal with the specified key.

Parameters

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Principal key to retrieve memberships for |

Returns

**object**: The principal as an object.

Retrieving the full principal for 'user1'

```typescript
import {getPrincipal} from '/lib/xp/auth';

const result = getPrincipal('user:system:user1');
```

Sample response

```js
({
    type: "user",
    key: "user:system:user1",
    displayName: "User 1",
    disabled: false,
    email: "user1@enonic.com",
    login: "user1",
    idProvider: "system",
    hasPassword: true
})
```

### getProfile

Returns the profile of a user.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Principal key to retrieve profile for |
| scope | string | <optional> | Optional scope setting |

Returns

**object**: Profile data.

Example

Retrieving the profile of 'user1'

```typescript
import {getProfile} from '/lib/xp/auth';

const result = getProfile({
    key: 'user:system:user1'
});
```

Sample response

```js
({
    nickName: "User Nick"
})
```

### getUser

Returns the logged-in user. If not logged-in, this will return *undefined* or *null*.

Parameters

None

Returns

**object**: [`User`](#user) data.

Example

Retrieving the profile of 'user1'

```typescript
import {getUser} from '/lib/xp/auth';

const result = getUser();
```

Sample response

```js
({
    type: "user",
    key: "user:system:user1",
    displayName: "User 1",
    disabled: false,
    email: "user1@enonic.com",
    login: "user1",
    idProvider: "system",
    hasPassword: true
})
```

### hasRole

Checks if the logged-in user has the specified role.

Parameters

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| role | string |  | The role to check for |

Returns

**boolean**: `true` if the current user has the role, `false` otherwise.

Example

Checking a role

```typescript
import {hasRole} from '/lib/xp/auth';

const hasRole = hasRole('system.admin');
```

### login

Logs in a user through the specified idProvider, with username and password.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| user | string |  | Mandatory name of the user to log in |
| password | string | <optional> | Password for the user. Ignored if skipAuth is set to true, mandatory otherwise. |
| idProvider | string | <optional> | Name of id provider where the user is stored. If not specified it will try all available id providers, in alphabetical order. |
| skipAuth | boolean | <optional> | Skip authentication. Default is `false` if not specified. |
| sessionTimeout | number | <optional> | Session timeout (in seconds). By default, the value of session.timeout from `com.enonic.xp.web.jetty.cfg` |
| scope XP 7.3.0 | string | <optional> | Defines the scope of the login. Valid values are `SESSION`, `REQUEST` and `NONE` (starting from version XP 7.8.0). When scope is set to `SESSION` the login is persistent. If scope is set to `REQUEST` the login is only valid for the current request. Scope `NONE` allows to check correctness of username and password without logging into the system. Default is `SESSION` if not specified. |

Returns

**object**: The login result.

Example

Logging in a user

```typescript
import {login} from '/lib/xp/auth';

const loginResult = login({
    user: 'user1',
    password: 'myPwd1',
    idProvider: 'myIdProvider'
});
```

Sample response

```js
({
    authenticated: true,
    user: {
        type: "user",
        key: "user:system:user1",
        displayName: "The One And Only",
        disabled: false,
        email: "user1@enonic.com",
        login: "user1",
        idProvider: "myIdProvider",
        hasPassword: true
    }
})
```

### logout

Logs out the currently logged-in user.

Parameters

None

Returns

**void**

### modifyGroup

Updates an existing group.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Principal key of the group to modify |
| editor | function |  | Group editor function |

Returns

**object**: The updated group.

Example

Changing a group

```typescript
import {modifyGroup} from '/lib/xp/auth';

// Callback to edit the group.
function groupEditor(c) {
    c.displayName = 'Modified display name';
    c.description = 'descriptionX';
    return c;
}

// Modify group with specified key.
const group = modifyGroup({
    key: 'group:system:group-a',
    editor: groupEditor
});
```

Sample response

```js
({
    type: "group",
    key: "group:system:group-a",
    displayName: "Modified display name",
    description: "descriptionX"
})
```

### modifyProfile

Updates an existing user profile. Will create a new profile, if an existing one with provided `scope` was not found.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Principal key of the user |
| scope | string | <optional> | Optional scope setting |
| editor | function |  | Profile editor function |

Returns

**object**: The updated profile.

Changing a profile

```typescript
import {modifyProfile} from '/lib/xp/auth';

// Callback to edit the profile.
function profileEditor(c) {
    if (!c) {
        c = {};
    }
    c.nickName = "User Nick";
    return c;
}

// Modify profile with specified key.
const profileModified = modifyProfile({
    key: 'user:system:user1',
    editor: profileEditor
});
```

Sample response

```js
({
    nickName: "User Nick"
})
```

### modifyRole

Updates an existing role.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | The role key |
| editor | function |  | Role editor function |

Returns

**object**: The updated role.

Changing a role

```typescript
import {modifyRole} from '/lib/xp/auth';

// Callback to edit the profile.
function roleEditor(c) {
    c.displayName = 'Nothing Role';
    c.description = 'This role does not give access to anything!';
    return c;
}

// Modify role with a specified key.
const theRole = modifyRole({
    key: 'role:aRole',
    editor: roleEditor
});
```

Sample response

```js
({
    type: "role",
    key: "role:aRole",
    displayName: "Nothing Role",
    description: "This role does not give access to anything!"
})
```

### modifyUser

Updates an existing user.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | The user key |
| editor | function |  | User editor function |

Returns

**object**: The updated [`User`](#user).

Changing a user

```typescript
import {modifyUser} from '/lib/xp/auth';

// Callback to edit the profile.
function userEditor(c) {
    c.displayName = 'User 1-A';
    c.email = 'user1a@enonic.com';
    return c;
}

// Modify user with a specified key.
const theUser = modifyUser({
    key: 'user:system:user1',
    editor: userEditor
});
```

Sample response

```js
({
    type: "user",
    key: "user:system:user1",
    displayName: "User 1-A",
    disabled: false,
    email: "user1a@enonic.com",
    login: "user1",
    idProvider: "myIdProvider",
    hasPassword: true
})
```

### removeMembers

Removes members from a principal (group or role).

Parameters

| Name | Kind | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | The principal key of a group or a role to remove members from |
| members | string[] |  | Principal keys to remove as members |

Returns

**void**

Remove members from a specified principal.

```typescript
authLib.removeMembers('role:roleId', ['user:system:user1', 'group:system:group-a']);
```

## Type Definitions

### User

Type

**object**

Properties

| Name | Type | Description |
| --- | --- | --- |
| type | string | The type of principal, always "user" for users |
| key | string | The unique key of the user |
| displayName | string | The display name of the user |
| modifiedTime | string | The last modified time of the user in ISO 8601 format |
| disabled | boolean | Whether the user is disabled or not |
| email | string | The email of the user |
| login | string | The login name of the user |
| idProvider | string | The id provider where the user is stored |
| hasPassword | boolean | XP 7.15.0 Whether the user has a password set |
