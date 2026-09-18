<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-auth generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-auth.md

# Auth library

Manage principals and authentication

> **Tip:** If, while using this API, you are getting authentication errors like "*Access denied to user [unknown]*" it means that user role in the current context lacks sufficient permissions (for example when executed from inside a service). In this case you must explicitly execute the function in the [context](docs/code/stable/libraries/lib-context.md#runcontext) of System Administrator role.

## Usage

```groovy
dependencies {
  include xplibs.auth
}
```

```typescript
import authLib from '/lib/xp/auth';
```

## Functions

### addMembers

Adds members to a principal (group or role).

Parameters

Takes the `principalKey` (a [GroupKey](docs/code/stable/fundamentals/types.md#group-key) or [RoleKey](docs/code/stable/fundamentals/types.md#role-key)) of the group or role to add members to, and an array of `members` — the [UserKey](docs/code/stable/fundamentals/types.md#user-key) or [GroupKey](docs/code/stable/fundamentals/types.md#group-key) values to add.

Returns

**void**

Example

Add members to a specified principal

```typescript
import {addMembers} from '/lib/xp/auth';

addMembers('role:roleId', ['user:system:user1', 'group:system:group-a']);
```

### changePassword

Changes or clears the password for the specified user.

Parameters

`changePassword()` takes a single `ChangePasswordParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| userKey | string | Key of the user to change password for. |
| password | string | **Optional.** The new password to set. If `null`, the password is cleared. |

Returns

**void**

Example

Change the password of the current user

```typescript
import {getUser, changePassword} from '/lib/xp/auth';

const user = getUser();

if (user) {
    changePassword({
        userKey: user.key,
        password: 'new-secret-password'
    });
}
```

### createGroup

Creates a group.

Parameters

`createGroup()` takes a single `CreateGroupParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| idProvider | string | Key of the id provider where the group will be created. |
| name | string | Group name. |
| displayName | string | **Optional.** Group display name. |
| description | string | **Optional.** Group description. |

Returns

**object** : ([`Group`](docs/code/stable/fundamentals/types.md#group)) The created group.

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

### createIdProvider

Creates an ID provider.

Parameters

`createIdProvider()` takes a single `CreateIdProviderParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | ID provider key. |
| displayName | string | ID provider display name. |
| description | string | **Optional.** ID provider description. |
| idProviderConfig | [IdProviderConfig](#id-provider-config) | **Optional.** Binds this provider to one application. Without it the provider is incomplete and login plumbing won’t resolve back to an app. |
| permissions | [IdProviderAccessControlEntry](#id-provider-access-control-entry)[] | **Optional.** ID provider permissions. |

Returns

**object** : ([`IdProvider`](#id-provider)) The created ID provider.

Example

Creating an ID provider

```typescript
import {createIdProvider} from '/lib/xp/auth';

const idProvider = createIdProvider({
    key: 'myIdProvider',
    displayName: 'My ID Provider',
    description: 'My ID provider description',
    idProviderConfig: {
        applicationKey: 'com.example.myidprovider',
        config: {
            // app-specific configuration
        }
    },
    permissions: [
        {
            principal: 'role:system.admin',
            access: 'ADMINISTRATOR'
        }
    ]
});
```

Sample response

```js
({
    key: "myIdProvider",
    displayName: "My ID Provider",
    description: "My ID provider description",
    idProviderConfig: {
        applicationKey: "com.example.myidprovider",
        config: {
            // app-specific configuration
        }
    }
})
```

### createRole

Creates a role.

Parameters

`createRole()` takes a single `CreateRoleParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| name | string | The name of the role. The key of the role will be `role:<name>`. |
| displayName | string | **Optional.** Role display name. |
| description | string | **Optional.** Role description. |

Returns

**object** : ([`Role`](docs/code/stable/fundamentals/types.md#role)) The created role.

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

`createUser()` takes a single `CreateUserParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| idProvider | string | Key of the id provider where the user will be created. |
| name | string | User login name. |
| displayName | string | **Optional.** User display name. |
| email | string | **Optional.** User e-mail. |

Returns

**object** : ([`User`](docs/code/stable/fundamentals/types.md#user)) The created user.

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

Takes the `principalKey` (a [PrincipalKey](docs/code/stable/fundamentals/types.md#principal-key)) of the principal to delete.

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

Parameters

`findPrincipals()` takes a single `FindPrincipalsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| type | [PrincipalType](docs/code/stable/fundamentals/types.md#principal-type) | **Optional.** Principal type to look for, one of `'user'`, `'group'` or `'role'`. If not specified all principal types are included. |
| idProvider | string | **Optional.** Key of the id provider to look for. If not specified, all id providers are included. |
| start | number | **Optional.** First principal to return from the search results. Used for pagination. Defaults to `0`. |
| count | number | **Optional.** A limit on the number of principals to return. Defaults to `10`. |
| name | string | **Optional.** Name of the principal to look for. |
| searchText | string | **Optional.** Text to look for in any principal field. |

Returns

**object** : ([`FindPrincipalsResult`](#find-principals-result)) The total number of principals matching the search, the count of principals included, and an array of hits containing the principals.

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
    total: 1,
    count: 1,
    hits: [
        {
            type: "user",
            key: "user:system:user1",
            displayName: "The One And Only",
            disabled: false,
            email: "user1@enonic.com",
            login: "user1",
            idProvider: "myIdProvider",
            hasPassword: true
        }
    ]
})
```

### findUsers

Search for users matching the specified query.

Parameters

`findUsers()` takes a single `FindUsersParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| query | string | Query expression. |
| start | number | **Optional.** Start index for paging. Defaults to `0`. |
| count | number | **Optional.** Number of users to fetch. Defaults to `10`. |
| sort | string | **Optional.** Sorting expression. |
| includeProfile | boolean | **Optional.** If set to `true`, the full profile of each user is included in the result. Defaults to `false`. |

Returns

**object** : ([`FindPrincipalsResult`](#find-principals-result)) The total number of hits, the number returned, and an array of the matching [`User`](docs/code/stable/fundamentals/types.md#user) objects.

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

> **Note:** If you want to find a user by key, you have to use the `_id` field in the `query` parameter.

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

Takes no arguments.

Returns

**string**: A suggestion for a secure password.

Example

Generate a password and return the password string

```typescript
import {generatePassword} from '/lib/xp/auth';

const pwd = generatePassword();
```

### getIdProviderConfig

Returns the ID provider configuration. Meant to be called from an ID provider implementation.

Parameters

Takes no arguments. The expected config shape can be supplied as a TypeScript type parameter, e.g. `getIdProviderConfig()`.

Returns

**object**: An object with all the values in the configuration, or `null` if no configuration is set.

Example

Reading a value from the ID provider configuration

```typescript
import {getIdProviderConfig} from '/lib/xp/auth';

const config = getIdProviderConfig<{ field?: string }>();

if (config) {
    log.info('Field value for the current ID provider config = %s', config.field);
}
```

### getIdProviders

Returns all id providers configured on the system. Each entry’s `idProviderConfig` is present only when the provider is bound to an application; incomplete providers come back without it.

Parameters

Takes no arguments.

Returns

**object[]** : ([`IdProvider`](#id-provider)[]) A list of ID providers.

Example

Retrieving all ID providers

```typescript
import {getIdProviders} from '/lib/xp/auth';

const idProviders = getIdProviders();
```

Sample response

```js
([
    {
        key: "system",
        displayName: "System Id Provider"
    },
    {
        key: "myIdProvider",
        displayName: "My ID Provider",
        description: "My ID provider description",
        idProviderConfig: {
            applicationKey: "com.example.myidprovider",
            config: {}
        }
    }
])
```

### getMembers

Returns a list of principals that are members of the specified principal.

Parameters

Takes the `principalKey` (a [GroupKey](docs/code/stable/fundamentals/types.md#group-key) or [RoleKey](docs/code/stable/fundamentals/types.md#role-key)) of the group or role to retrieve members for.

Returns

**object[]** : ([`User`](docs/code/stable/fundamentals/types.md#user) | [`Group`](docs/code/stable/fundamentals/types.md#group))[] A list of users and groups that are members of the principal, or an empty array if none.

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

Takes the `principalKey` (a [UserKey](docs/code/stable/fundamentals/types.md#user-key) or [GroupKey](docs/code/stable/fundamentals/types.md#group-key)) of the user or group to retrieve memberships for, and an optional `transitive` boolean — retrieve transitive memberships. Considered `false` if not specified.

Returns

**object[]** : ([`Group`](docs/code/stable/fundamentals/types.md#group) | [`Role`](docs/code/stable/fundamentals/types.md#role))[] A list of groups and roles that the specified principal is a member of.

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
    displayName: "Administrator"
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
    {
        type: "role",
        key: "role:system.admin.login",
        displayName: "Login to administration console"
    },
    {
        type: "group",
        key: "group:system:content-managers",
        displayName: "Content Managers"
    },
    {
        type: "role",
        key: "role:cms.expert",
        displayName: "CMS Expert"
    },
    {
        type: "role",
        key: "role:cms.project.default.editor",
        displayName: "Default project editor"
    }
]
```

### getPrincipal

Returns the principal with the specified key. The result is narrowed to [`User`](docs/code/stable/fundamentals/types.md#user), [`Group`](docs/code/stable/fundamentals/types.md#group) or [`Role`](docs/code/stable/fundamentals/types.md#role) when the key type makes the principal type unambiguous.

Parameters

Takes the `principalKey` (a [PrincipalKey](docs/code/stable/fundamentals/types.md#principal-key)) of the principal to look for.

Returns

**object** : ([`Principal`](docs/code/stable/fundamentals/types.md#principal)) The principal as an object, or `null` if it does not exist.

Example

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

`getProfile()` takes a single `GetProfileParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | [UserKey](docs/code/stable/fundamentals/types.md#user-key) | Principal key of the user. |
| scope | string | **Optional.** Scope of the data to retrieve. |

Returns

**object**: Profile data, or `null` if the user was not found.

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

Returns the logged-in user. If not logged-in, this will return `null`.

Parameters

`getUser()` takes an optional `GetUserParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| includeProfile | boolean | **Optional.** If set to `true`, the user’s profile is included in the result as a `profile` property. Defaults to `false`. |

Returns

**object** : ([`User`](docs/code/stable/fundamentals/types.md#user)) The logged-in user, or `null` if not logged in. When `includeProfile` is `true`, the user also carries a `profile` property.

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

Takes the `role` name (a string) to check for.

Returns

**boolean**: `true` if the current user has the role, `false` otherwise.

Example

Checking a role

```typescript
import {hasRole} from '/lib/xp/auth';

const isAdmin = hasRole('system.admin');
```

### login

Logs in a user through the specified idProvider, with username and password.

Parameters

`login()` takes a single `LoginParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| user | string | Name of the user to log in. |
| password | string | **Optional.** Password for the user. Ignored if `skipAuth` is `true`, required otherwise. |
| idProvider | string | **Optional.** Name of the id provider where the user is stored. If not specified the system id provider is used. |
| skipAuth | boolean | **Optional.** Skip authentication. Defaults to `false`. |
| sessionTimeout | number | **Optional.** Session timeout, in seconds. Defaults to the value of `session.timeout` from `com.enonic.xp.web.jetty.cfg`. |
| scope | [LoginScopeType](#login-scope-type) | **Optional.** Scope of the login. When set to `SESSION` the login is persistent; `REQUEST` makes it valid only for the current request; `NONE` checks the username and password without logging into the system. Defaults to `SESSION`. |

Returns

**object** : ([`LoginResult`](#login-result)) The login result.

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

Takes no arguments.

Returns

**void**

### modifyGroup

Updates an existing group.

Parameters

`modifyGroup()` takes a single `ModifyGroupParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | [GroupKey](docs/code/stable/fundamentals/types.md#group-key) | Principal key of the group to modify. |
| editor | function | Editor callback `(group: Group) => Group` that receives the current [`Group`](docs/code/stable/fundamentals/types.md#group) and returns the modified group. |

Returns

**object** : ([`Group`](docs/code/stable/fundamentals/types.md#group)) The updated group, or `null` if the group was not found.

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

`modifyProfile()` takes a single `ModifyProfileParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | [UserKey](docs/code/stable/fundamentals/types.md#user-key) | Principal key of the user. |
| scope | string | **Optional.** Scope of the data to retrieve and update. |
| editor | function | Editor callback `(profile: Profile) => Profile` that receives the current profile and returns the modified profile. |

Returns

**object**: The updated profile, or `null` if the user was not found.

Example

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

`modifyRole()` takes a single `ModifyRoleParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | [RoleKey](docs/code/stable/fundamentals/types.md#role-key) | Principal key of the role to modify. |
| editor | function | Editor callback `(role: Role) => Role` that receives the current [`Role`](docs/code/stable/fundamentals/types.md#role) and returns the modified role. |

Returns

**object** : ([`Role`](docs/code/stable/fundamentals/types.md#role)) The updated role, or `null` if the role was not found.

Example

Changing a role

```typescript
import {modifyRole} from '/lib/xp/auth';

// Callback to edit the role.
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

`modifyUser()` takes a single `ModifyUserParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | [UserKey](docs/code/stable/fundamentals/types.md#user-key) | Principal key of the user to modify. |
| editor | function | Editor callback `(user: User) => User` that receives the current [`User`](docs/code/stable/fundamentals/types.md#user) and returns the modified user. |

Returns

**object** : ([`User`](docs/code/stable/fundamentals/types.md#user)) The updated user, or `null` if the user was not found.

Example

Changing a user

```typescript
import {modifyUser} from '/lib/xp/auth';

// Callback to edit the user.
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

Takes the `principalKey` (a [GroupKey](docs/code/stable/fundamentals/types.md#group-key) or [RoleKey](docs/code/stable/fundamentals/types.md#role-key)) of the group or role to remove members from, and an array of `members` — the [UserKey](docs/code/stable/fundamentals/types.md#user-key) or [GroupKey](docs/code/stable/fundamentals/types.md#group-key) values to remove.

Returns

**void**

Example

Remove members from a specified principal

```typescript
import {removeMembers} from '/lib/xp/auth';

removeMembers('role:roleId', ['user:system:user1', 'group:system:group-a']);
```

## Type Definitions

The core principal types — [`User`](docs/code/stable/fundamentals/types.md#user), [`Group`](docs/code/stable/fundamentals/types.md#group), [`Role`](docs/code/stable/fundamentals/types.md#role), [`Principal`](docs/code/stable/fundamentals/types.md#principal), and the key types [`PrincipalKey`](docs/code/stable/fundamentals/types.md#principal-key), [`UserKey`](docs/code/stable/fundamentals/types.md#user-key), [`GroupKey`](docs/code/stable/fundamentals/types.md#group-key), [`RoleKey`](docs/code/stable/fundamentals/types.md#role-key) and [`PrincipalType`](docs/code/stable/fundamentals/types.md#principal-type) — are shared across the libraries and defined on the [Types](docs/code/stable/fundamentals/types.md) page.

### LoginScopeType

A string union: `'SESSION' | 'REQUEST' | 'NONE'`. Controls how long a successful login stays valid — see the `scope` property of `login()`.

### LoginResult

Properties

| Name | Type | Description |
| --- | --- | --- |
| authenticated | boolean | Whether the user was successfully authenticated. |
| user | [User](docs/code/stable/fundamentals/types.md#user) | **Optional.** The authenticated user. Present when `authenticated` is `true`. |
| message | string | **Optional.** A message describing the result, typically present on failure. |

### FindPrincipalsResult

The result of `findPrincipals()` and `findUsers()`.

Properties

| Name | Type | Description |
| --- | --- | --- |
| total | number | Total number of principals matching the search. |
| count | number | Number of principals included in `hits`. |
| hits | [Principal](docs/code/stable/fundamentals/types.md#principal)[] | The matching principals. For `findUsers()` the hits are [`User`](docs/code/stable/fundamentals/types.md#user) objects. |

### IdProvider

Properties

| Name | Type | Description |
| --- | --- | --- |
| key | string | ID provider key. |
| displayName | string | ID provider display name. |
| description | string | **Optional.** ID provider description. |
| idProviderConfig | [IdProviderConfig](#id-provider-config) | **Optional.** Present only when the provider is bound to an application. |

### IdProviderConfig

Properties

| Name | Type | Description |
| --- | --- | --- |
| applicationKey | string | Key of the application whose functions serve requests for this provider. |
| config | object | **Optional.** Per-instance configuration tree passed to the bound application. |

### IdProviderAccessControlEntry

Properties

| Name | Type | Description |
| --- | --- | --- |
| principal | [PrincipalKey](docs/code/stable/fundamentals/types.md#principal-key) | Principal the entry grants access to. |
| access | [IdProviderAccess](#id-provider-access) | Permission level. |

### IdProviderAccess

A string union of permission levels: `'READ' | 'CREATE_USERS' | 'WRITE_USERS' | 'ID_PROVIDER_MANAGER' | 'ADMINISTRATOR'`.
