<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-context generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-context.md

# Context library

This API provides functions to access and use the current context.

## Usage

```groovy
dependencies {
  include xplibs.context
}
```

```typescript
import contextLib from '/lib/xp/context';
```

## Functions

### get

Returns the current context.

Parameters

`get()` takes no arguments.

Returns

**object** : ([`Context`](#Context)) The current context. The `attributes` field is always present (possibly empty); `branch`, `repository`, and `authInfo` are present when set on the calling context.

Example

Getting the current context

```typescript
const context = contextLib.get();
```

Sample response

```typescript
{
  branch: "draft",
  repository: "com.enonic.cms.default",
  authInfo: {
      user: {                            (1)
          type: "user",
          key: "user:system:abc",
          displayName: "A.B.C.",
          disabled: false,
          email: "abc@enonic.com",
          login: "abc",
          idProvider: "system",
          hasPassword: true
      },
      principals: [
          "user:system:abc",
          "role:system.admin",
          "role:system.admin.login",
          "role:system.authenticated",
          "role:system.everyone"
      ]
  },
  attributes: {
     optionalAttributes: "of any kind"
  }
}
```

| ****1** | The `user` field is only set when a user is logged in. |
| --- | --- |

### run

Runs a function inside a custom context, for instance the one returned by the `get()` function call. Commonly used when accessing repositories, or to override the current user’s permissions.

Parameters

`run()` takes two positional arguments: a [`ContextParams`](#ContextParams) object defining the context for the scope of the callback (any field omitted is inherited from the current context), and a callback function to execute. The callback’s return value is propagated as the return value of `run()`.

Returns

**any** : Whatever the callback returns.

Example

Run a function in a different context

```typescript
import {run} from '/lib/xp/context';

const result = run({
    repository: 'system-repo',
    branch: 'master',
    user: {
        login: 'su',
        idProvider: 'system'
    },
    principals: ['role:system.admin'],
    attributes: {
        ignorePublishTimes: true
    }
}, () => 'Hello from context');
```

Sample response

```typescript
"Hello from context"
```

## Type Definitions

### Context

The shape of the object returned by `get()`.

Properties

| Name | Type | Description |
| --- | --- | --- |
| attributes | [ContextAttributes](#ContextAttributes) | Custom attributes set on the context. Always present; may be empty. |
| branch | string | **Optional.** Branch context. |
| repository | string | **Optional.** Repository context. |
| authInfo | [AuthInfo](#AuthInfo) | **Optional.** Authentication information for the current context. |

### ContextParams

The context object passed as the first argument to `run()`. Any field omitted is inherited from the calling context.

Properties

| Name | Type | Description |
| --- | --- | --- |
| repository | string | **Optional.** Repository to run the callback in. Defaults to the current repository. |
| branch | string | **Optional.** Branch to run the callback in. Defaults to the current branch. |
| user | [ContextUserParams](#ContextUserParams) | **Optional.** User to run the callback as. |
| principals | [PrincipalKey](docs/code/stable/fundamentals/types.md#principal-key)[] | **Optional.** Additional principal keys (users, groups, and roles) to attach to the authentication info for the duration of the callback. |
| attributes | [ContextAttributes](#ContextAttributes) | **Optional.** Additional context attributes. |

### AuthInfo

Authentication information attached to a context.

Properties

| Name | Type | Description |
| --- | --- | --- |
| user | [User](docs/code/stable/fundamentals/types.md#user) | **Optional.** The currently authenticated user. Omitted when no user is logged in. |
| principals | [PrincipalKey](docs/code/stable/fundamentals/types.md#principal-key)[] | **Optional.** Principal keys (users, groups, and roles) attached to the authentication info. |

### ContextUserParams

Identifies the user to run a callback as, passed in `[ContextParams](#ContextParams).user`.

Properties

| Name | Type | Description |
| --- | --- | --- |
| login | string | Login name of the user. |
| idProvider | string | **Optional.** Key of the ID provider the user belongs to. Defaults to the system ID provider when omitted. |

### ContextAttributes

A record of custom context attributes. Keys are strings; only values of type `number`, `string`, `boolean`, or plain `object` are supported.
