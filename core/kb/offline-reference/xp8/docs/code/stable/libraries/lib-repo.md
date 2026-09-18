<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-repo generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-repo.md

# Repo library

Functions related to management of a node repository.

## Usage

```groovy
dependencies {
  include xplibs.repo
}
```

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

For more information on events, check out the [Event library](docs/code/stable/libraries/lib-event.md)

## Functions

### create

Creates a repository.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params | [CreateRepositoryParams](#createrepositoryparams) | JSON with the parameters |

Returns

**[Repository](#repository)** : The created repository.

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
            principal: 'role:admin',
            allow: [
                'READ',
                'CREATE',
                'MODIFY',
                'DELETE',
                'PUBLISH',
                'READ_PERMISSIONS',
                'WRITE_PERMISSIONS'
            ],
            deny: []
        }
    ],
    rootChildOrder: '_ts DESC',
    transient: true
});

log.info('Repository created with id %s', result2.id);
```

```typescript
// First repository created.
const expected1 = {
    id: 'test-repo',
    transient: false,
    branches: [
        'master'
    ],
    data: {}
};
```

### createBranch

Creates a branch.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params | [CreateBranchParams](#createbranchparams) | JSON with the parameters |

Returns

**[BranchResult](#branchresult)** : The created branch.

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

### deleteRepo

Deletes a repository.

> **Note:** Renamed from `delete` to avoid the JavaScript reserved word. The old `delete` export is still available for backward compatibility.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| id | string | Repository ID |

Returns

**boolean** : `true` if deleted, `false` otherwise

Examples

```typescript
import {deleteRepo} from '/lib/xp/repo';

// Deletes a repository
const result = deleteRepo('test-repo');

if (result) {
    log.info('Repository deleted');
} else {
    log.info('Repository was not found');
}
```

### deleteBranch

Deletes a branch.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params | [DeleteBranchParams](#deletebranchparams) | JSON with the parameters |

Returns

**[BranchResult](#branchresult)** : The deleted branch.

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

Retrieves a repository.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| id | string | Repository ID |

Returns

**[Repository](#repository) | null** : The repository, or `null` if no repository exists with the given id.

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
    id: 'test-repo',
    transient: false,
    branches: [
        'master'
    ],
    data: {}
};
```

### getBinary

Returns a data stream for a repository attachment.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params | [GetRepositoryBinaryParams](#getrepositorybinaryparams) | JSON with the parameters |

Returns

**\*** : Stream of the attachment data.

Example

```typescript
import {getBinary} from '/lib/xp/repo';

const binaryStream = getBinary({
    repoId: 'my-repo',
    binaryReference: 'myBinaryReference'
});
```

### list

Retrieves the list of repositories.

Returns

**[Repository](#repository)[]** : The list of repositories.

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
    id: 'test-repo',
    transient: false,
    branches: [
        'master'
    ],
    data: {}
}, {
    id: 'another-repo',
    transient: false,
    branches: [
        'master'
    ],
    data: {}
}];
```

### modify

Updates a repository.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params | [ModifyRepositoryParams](#modifyrepositoryparams) | JSON with the parameters |

Returns

**[Repository](#repository)** : The updated repository.

Example

```typescript
import {modify} from '/lib/xp/repo';

// Update repository data
const result = modify({
    id: 'my-repo',
    editor: (repo) => {
        repo.transient = true;
        repo.data = {
            ...repo.data,
            myString: 'modified',
            myArray: ['modified1', 'modified2', 'modified3']
        };
        return repo;
    }
});
```

### refresh

Refreshes indices in the current repository.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| params | [RefreshParams](#refreshparams) | **Optional.** JSON with the parameters. |

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

## Type Definitions

### Repository

Repository object returned by `create`, `get`, `list`, and `modify`.

Properties

| Name | Type | Description |
| --- | --- | --- |
| id | string | Repository ID. |
| branches | string[] | Branches available in the repository. |
| data | object | **Optional.** Repository data as a key/value map. |
| transient | boolean | `true` if the repository is transient (excluded from dumps and snapshots). |

### CreateRepositoryParams

Object to pass to the `create` function.

Properties

| Name | Type | Description |
| --- | --- | --- |
| id | string | Repository ID. |
| rootPermissions | [AccessControlEntry](#accesscontrolentry)[] | **Optional.** Array of root permissions. By default, all permissions to `role:system.admin` and `READ` permission to `role:system.authenticated`. |
| rootChildOrder | string | **Optional.** Root child order (for example, `_ts DESC`). |
| transient | boolean | **Optional.** Mark the repository as transient. Defaults to `false`. |

### AccessControlEntry

Permission entry used in `CreateRepositoryParams.rootPermissions`.

Properties

| Name | Type | Description |
| --- | --- | --- |
| principal | string | Principal key (for example, `role:system.admin`, `user:system:su`). |
| allow | string[] | **Optional.** Permissions to grant. Each value is one of `READ`, `CREATE`, `MODIFY`, `DELETE`, `PUBLISH`, `READ_PERMISSIONS`, `WRITE_PERMISSIONS`. |
| deny | string[] | **Optional.** Permissions to deny. Same set of values as `allow`. |

### CreateBranchParams

Object to pass to the `createBranch` function.

Properties

| Name | Type | Description |
| --- | --- | --- |
| branchId | string | Branch ID. |
| repoId | string | Repository where the branch should be created. |

### DeleteBranchParams

Object to pass to the `deleteBranch` function.

Properties

| Name | Type | Description |
| --- | --- | --- |
| branchId | string | Branch ID. |
| repoId | string | Repository where the branch should be deleted. |

### BranchResult

Object returned by `createBranch` and `deleteBranch`.

Properties

| Name | Type | Description |
| --- | --- | --- |
| id | string | Branch ID. |

### ModifyRepositoryParams

Object to pass to the `modify` function.

Properties

| Name | Type | Description |
| --- | --- | --- |
| id | string | Repository ID. |
| editor | function | Editor callback function. Receives the current `[Repository](#repository)` and must return the modified repository. |

### GetRepositoryBinaryParams

Object to pass to the `getBinary` function.

Properties

| Name | Type | Description |
| --- | --- | --- |
| repoId | string | Repository ID. |
| binaryReference | string | Reference to the binary. |

### RefreshParams

Object to pass to the `refresh` function.

Properties

| Name | Type | Description |
| --- | --- | --- |
| mode | string | **Optional.** Index type to be refreshed. One of `all`, `search`, or `storage`. Defaults to `all`. |
| repo | string | **Optional.** Repository ID. Defaults to the repository of the current context. |
| branch | string | **Optional.** Branch. Defaults to the branch of the current context. |
