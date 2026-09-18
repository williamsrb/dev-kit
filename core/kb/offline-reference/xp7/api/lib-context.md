<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-context generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-context.md

# Context API

This API provides functions to access and use the current context.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-context:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import contextLib from '/lib/xp/context';
```

## Functions

### get

Returns the current context

Parameters

None

Returns

[GetContext](#getcontext)

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
          key: "user.system.abc",
          displayName: "A.B.C.",
          disabled: false,
          email: "abc@enonic.com",
          login: "abc",
          idProvider: "system"
      }
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

| ****1** | The user node will not be returned unless there is a logged-in user. |
| --- | --- |

### run

Runs a function inside a custom context, for instance the one returned by the `get()` function call. Commonly used when accessing repositories, or to override current users permissions.

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| context | object | [RunContext](#runcontext) to be used for the scope of the callback function |
| callback | function | Function to execute |

Returns

**string** : The result of the execution.

Example

Run a simple function in a different context

```typescript
// Define the callback to be executed.
function callback() {
    return 'Hello from context';
}

// Executes function within a custom context.
const result = contextLib.run(context, callback);
```

Sample response

```typescript
"Hello from context"
```

## Objects

### GetContext

The context object is always available within the scope of a request

Sample context object

```typescript
{
  repository: "some.repo.name", (1)
  branch: "master", (2)
  authInfo: {
      user: { (3)
          login: "mylogin",
          idProvider: "idprovidername"
      },
      principals: ["role:system.admin"] (4)
  },
  attributes: { (5)
     optionalAttributes: "of any kind"
  }
}
```

| ****1** | **repository** (*string*) Repository context. |
| --- | --- |
| ****2** | **branch** (*string*) Branch context. |
| ****3** | **user** (*object*) Specify a valid user/ID provider combination |
| ****4** | **principals** (*object*) Roles or group principals applicable for current user |
| ****5** | **attributes** (*object*) custom attributes XP 7.8.0 |

### RunContext

The context object is always available within the scope of a request

Sample context object

```typescript
{
  repository: "some.repo.name", (1)
  branch: "master", (2)
  user: { (3)
      login: "mylogin",
      idProvider: "idprovidername"
  },
  principals: ["role:system.admin"], (4)
  attributes: { (5)
     optionalAttributes: "of any kind"
  }
}
```

| ****1** | **repository** (*string*) Repository context. |
| --- | --- |
| ****2** | **branch** (*string*) Branch context. |
| ****3** | **user** (*object*) Specify a valid user/idprovider combination |
| ****4** | **principals** (*object*) Roles or group principals applicable for current user |
| ****5** | **attributes** (*object*) custom attributes XP 7.8.0 |
