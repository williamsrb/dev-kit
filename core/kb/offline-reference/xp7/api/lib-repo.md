<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-repo generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-repo.md

# Repo API

Functions related to management of a node repository.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-repo:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import repoLib from '/lib/xp/repo';
```

## Events

Usage of this API produces the following events:

| Event | Occurs when |
| --- | --- |
| repository.created | a repository is created |
| repository.updated | a repository is updated |
| repository.deleted | a repository is deleted |
| repository.restoreInitialized | a repository restore begins |
| repository.restored | a repository restore is completed |

For more information on events, check out the [event API](/docs/platform/7.x/api/lib-event)

## Functions

### create

Creates a repository.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params | [CreateRepositoryParams](#createrepositoryparams) | JSON with the parameters |

Returns

**object** : Repository created as JSON

Examples

```typescript
import {create} from '/lib/xp/repo';

// Creates a repository with default configuration
const result1 = create({
    id: 'test-repo'
});

log.info('Repository created with id %s', result1.id);
```

```typescript
import {create} from '/lib/xp/repo';

// Creates a repository with specific settings
const result2 = create({
    id: 'test-repo2',
    rootPermissions: [
        {
            principal: "role:admin",
            allow: [
                "READ",
                "CREATE",
                "MODIFY",
                "DELETE",
                "PUBLISH",
                "READ_PERMISSIONS",
                "WRITE_PERMISSIONS"
            ],
            deny: []
        }
    ],
    rootChildOrder: "_ts DESC"
});

log.info('Repository created with id %s', result2.id);
```

```typescript
// First repository created.
const expected1 = {
    id: "test-repo",
    branches: [
        "master"
    ],
    settings: {}
};
```

### createBranch

Creates a branch

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params | [CreateBranchParams](#createbranchparams) | JSON with the parameters |

Returns

**object** : The branch (as JSON)

Examples

```typescript
import {createBranch} from '/lib/xp/repo';

// Creates a branch
try {
    const result = createBranch({
        branchId: 'test-branch',
        repoId: 'my-repo'
    });
    log.info('Branch [%s] created', result.id);
} catch (e) {
    if (e.code == 'branchAlreadyExists') {
        log.error('Branch [features-branch] already exist');
    } else {
        log.error('Unexpected error: %s', e.message);
    }
}
```

### delete

Deletes a repository

Parameters

| Name | Type | Description |
| --- | --- | --- |
| id | string | Repository ID |

Returns

**boolean** : `true` if deleted, `false` otherwise

Examples

```typescript
import {delete as deleteRepo} from '/lib/xp/repo';

// Deletes a repository
const result = deleteRepo('test-repo');

if (result) {
    log.info('Repository deleted');
} else {
    log.info('Repository was not found');
}
```

### deleteBranch

Deletes a branch

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params | [DeleteBranchParams](#deletebranchparams) | JSON with the parameters |

Returns

**object** : The branch (as JSON)

Examples

```typescript
import {deleteBranch} from '/lib/xp/repo';

// Deletes a branch
try {
    const result = deleteBranch({
        branchId: 'test-branch',
        repoId: 'my-repo'
    });
    log.info('Branch [%s] deleted', result.id);
} catch (e) {
    if (e.code == 'branchNotFound') {
        log.error('Branch [test-branch] does not exist');
    } else {
        log.error('Unexpected error: %s', e.message);
    }
}
```

### get

Retrieves a repository

Parameters

| Name | Type | Description |
| --- | --- | --- |
| id | string | Repository ID |

Returns

**object** : The repository (as JSON)

Examples

```typescript
import {get as getRepo} from '/lib/xp/repo';

// Retrieves a repository
const result = getRepo('test-repo');

if (result) {
    log.info('Repository found');
} else {
    log.info('Repository was not found');
}
```

```typescript
// Repository retrieved.
const expected = {
    id: "test-repo",
    branches: [
        "master"
    ],
    settings: {}
};
```

### list

Retrieves the list of repositories

Returns

**object** : The repositories (as JSON array)

Examples

```typescript
import {list} from '/lib/xp/repo';

// Retrieves the list of repositories
const result = list();
log.info('%s repositories found', result.length);
```

```typescript
// Repositories retrieved.
const expected = [{
    id: "test-repo",
    branches: [
        "master"
    ],
    settings: {}
}, {
    id: "another-repo",
    branches: [
        "master"
    ],
    settings: {}
}];
```

### refresh

Refreshes indices in the current repository

Parameters

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| params | [RefreshParams](#refreshparams) | <nullable> | JSON with the parameters |

Examples

```typescript
import {refresh} from '/lib/xp/repo';

// Refresh all for default repository
refresh();
```

```typescript
// Refresh storage for default repository
refresh({mode: 'storage'});
```

```typescript
// Refresh search for 'system-repo' repository
refresh({
    mode: 'search',
    repo: 'system-repo'
});
```

## Objects

### CreateRepositoryParams

Object to pass to the `create` function.

Fields

| Name | Type | Attributes | Details |
| --- | --- | --- | --- |
| id | string |  | Repository ID |
| rootPermissions | array | <optional> | Array of root permissions. By default, all permissions to 'system.admin' and read permission to 'system.authenticated' |
| settings | [RepositorySettings](#repositorysettings) | <optional> | Repository settings |
| transient | boolean | <optional> | If true, the repository will be transient |

### RepositorySettings

Repository settings to optionally pass to the `create` function

Fields

| Name | Type | Attributes | Details |
| --- | --- | --- | --- |
| definitions | [IndexDefinitions](#indexdefinitions) | <optional> | Index definitions |

### IndexDefinitions

Index definitions used in [RepositorySettings](#repositorysettings) parameter

Fields

| Name | Type | Attributes | Details |
| --- | --- | --- | --- |
| search | [IndexDefinition](#indexdefinition) | <optional> | Search index definition |
| version | [IndexDefinition](#indexdefinition) | <optional> | Version index definition |
| branch | [IndexDefinition](#indexdefinition) | <optional> | Branch indexes definition |

### IndexDefinition

Fields

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| settings | object | <optional> | Index definition settings |
| mapping | object | <optional> | Index definition settings |

### CreateBranchParams

Create branch parameters JSON

Fields

| Name | Type | Description |
| --- | --- | --- |
| branchId | string | Branch ID |
| repoId | string | Repository where the branch should be created |

### DeleteBranchParams

Delete branch parameters JSON

Fields

| Name | Type | Description |
| --- | --- | --- |
| branchId | string | Branch ID |
| repoId | string | Repository where the branch should be deleted |

### RefreshParams

Refresh parameters JSON

Fields

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| mode | string | <optional> | 'all' | Index definition settings |
| repo | string | <optional> | 'com.enonic.cms.default' | Repository id: 'com.enonic.cms.default' \| 'system-repo'. Default is the current repository set in portal |
| branch | string | <optional> | 'branch'=master | Branch |
