<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-node generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-node.md

# Node library

This API provides functions to get, query and manipulate nodes.

> **Warning:** **Do not use `lib-node` against the CMS (content) repository.** Content is layered on top of nodes with content-type validation, draft/master synchronization, publish-state bookkeeping, audit-log entries, child-project propagation, and indexing of system fields. Direct `lib-node` writes against a content node bypass all of that and corrupt the content model.

Use [`lib-content`](docs/code/stable/libraries/lib-content.md) for content. Reach for `lib-node` only when working with custom (non-content) repositories. See [Editors](docs/code/stable/storage/editors.md) for the pattern.

## Usage

```groovy
dependencies {
  include xplibs.node
}
```

```typescript
import nodeLib from '/lib/xp/node';
```

## Events

Usage of this API produces the following events:

| Event | Occurs when |
| --- | --- |
| node.created | a node is created |
| node.deleted | a node is deleted |
| node.pushed | a node is pushed to a different branch |
| node.duplicated | a node is duplicated |
| node.updated | a node is updated |
| node.moved | a node is moved in the tree structure |
| node.renamed | a node is renamed |
| node.sorted | a node is sorted |
| node.stateUpdated | a node state is updated |

For information on events, check out the [Event library](docs/code/stable/libraries/lib-event.md)

## Functions

### connect

Creates a connection to a repository with a given branch and authentication info.

Parameters

`connect()` takes a single `ConnectParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| repoId | string | Repository ID. |
| branch | string | Branch ID. |
| principals | [PrincipalKey](docs/code/stable/fundamentals/types.md#principal-key)[] | **Optional.** Additional principals to execute the connection with. |
| user | [ConnectUser](#connect-user) | **Optional.** User to execute the connection as. Defaults to the current user. |

Returns

**[RepoConnection](#repoconnection)** : A new connection to the repository

Example

Connect to repo 'my-repo', branch 'master'.

```typescript
import {connect} from '/lib/xp/node';

const connection = connect({
    repoId: 'my-repo',
    branch: 'master'
});
```

### multiRepoConnect

Creates a connection to several repositories with a given branch and authentication info.

Parameters

`multiRepoConnect()` takes a single `MultiRepoConnectParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| sources | [ConnectParams](#connect-params)[] | Repositories to connect to. The `user` property is not allowed on entries here. |

Returns

**[MultiRepoConnection](#multirepoconnection)** : A new connection object for all connected repositories.

Example

Connect to repos 'myRepo' and 'my-other-repo', both on branch 'master'.

```typescript
import {multiRepoConnect} from '/lib/xp/node';

const searchConnection = multiRepoConnect({
    sources: [
        {
            repoId: 'my-repo',
            branch: 'myBranch',
            principals: ["role:system.admin"]
        },
        {
            repoId: 'my-other-repo',
            branch: 'master',
            principals: ["role:system.admin"]
        }
    ]
});
```

## MultiRepoConnection

A MultiRepoConnection makes it possible to search across multiple repositories. The object has only one method: `query`.

### query

Queries nodes in a multi-repo connection.

Parameters

`query()` takes a single `QueryNodeParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| query | string/object | **Optional.** Query string or [DSL](docs/code/stable/storage/querying.md) expression. |
| start | number | **Optional.** Start index used for paging. Defaults to `0`. |
| count | number | **Optional.** Number of nodes to fetch, used for paging. Defaults to `10`. |
| filters | object | **Optional.** Query filters. |
| sort | string/object | **Optional.** Sorting string or [DSL](docs/code/stable/storage/querying.md#sort) expression. Defaults to `_score DESC`. |
| aggregations | object | **Optional.** [Aggregations](docs/code/stable/storage/aggregations.md) config. |
| highlight | object | **Optional.** [Highlighting](docs/code/stable/storage/highlighting.md) config. |
| suggestions | object | **Optional.** Term suggestions config, keyed by suggestion name. |
| explain | boolean | **Optional.** If set to `true`, score calculation explanation will be included in result. |

Returns

**object** : ([NodeMultiRepoQueryResult](#node-multi-repo-query-result)) Query result, where each hit also carries its `repoId` and `branch`.

Example

Query multi-repo connection

```typescript
const result = multiRepoConnection.query({
    start: 0,
    count: 2,
    query: "startTime > instant('2016-10-11T14:38:54.454Z')",
    filters: {
        boolean: {
            must: {
                exists: {
                    field: "modifiedTime"
                }
            },
            mustNot: {
                hasValue: {
                    field: "myField",
                    values: [
                        "cheese",
                        "fish",
                        "onion"
                    ]
                }
            }
        },
        notExists: {
            field: "unwantedField"
        },
        ids: {
            values: ["id1", "id2"]
        }
    }
});
```

Sample response

```typescript
const expected = {
    total: 12902,
    count: 2,
    hits: [
        {
            id: "b186d24f-ac38-42ca-a6db-1c1bda6c6c26",
            score: 1.2300000190734863,
            repoId: "my-repo",
            branch: "master"
        },
        {
            id: "350ba4a6-589c-498b-8af0-f183850e1120",
            score: 1.399999976158142,
            repoId: "com.enonic.cms.default",
            branch: "draft"
        }
    ]
}
```

## RepoConnection

A single-repo connection with various methods for working in a single repo.

All the examples below are using a repo connection to execute the functions. The repo connection can be created like this:

Connecting to a repo.

```typescript
import {connect} from '/lib/xp/node';

const repo = connect({
    repoId: "com.enonic.cms.default",
    branch: "master"
});
```

### commit

Commits the active version of nodes.

Parameters

`commit()` takes a single `CommitParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| keys | string/string[] | Node keys to commit. Each key can be an id or a path. Prefer ids over paths. |
| message | string | **Optional.** Commit message. |

Returns

**object** : ([NodeCommit](#node-commit)) A single commit, created and applied to all the nodes referenced in `keys`.

Example

Committing a node.

```typescript
const result1 = repo.commit({keys: 'nodeId'});
```

Sample response

```typescript
const expected = {
    id: "aa1f76bf-4bb9-41be-b166-03561c1555b2",
    message: "",
    committer: "user:system:anonymous",
    timestamp: "2019-01-24T15:16:36.260799Z"
}
```

Committing nodes.

```typescript
const result2 = repo.commit({
    keys: ['nodeId', 'nodeId2'],
    message: 'Commit message'
});
```

Sample response

```typescript
const expected = {
    id: "aa1f76bf-4bb9-41be-b166-03561c1555b2",
    message: "Commit message",
    committer: "user:system:anonymous",
    timestamp: "2019-01-24T15:19:30.818029Z"
}
```

### create

Creates a node. To create a node where the name is not important and there can be multiple instances under the same parent, skip the `_name` property and specify a `displayName`.

Parameters

`create()` takes a single `CreateNodeParams` object. Alongside the node’s own data, it accepts these reserved properties:

| Name | Type | Description |
| --- | --- | --- |
| `_name` | string | **Optional.** Name of the node. |
| `_parentPath` | string | **Optional.** Path to place the node under. |
| `_indexConfig` | object | **Optional.** How the document should be [indexed](docs/code/stable/storage/indexing.md). A default template value "[byType](docs/code/stable/storage/indexing.md#byType)" will be set if no value is specified. |
| `_permissions` | object[] | **Optional.** The access control list for the node. By default the creator will have full access. |
| `_inheritsPermissions` | boolean | **Optional.** Set to `true` if the permissions should be inherited from the node parent. This is a meta-property and is not persisted. Defaults to `false`. |
| `_manualOrderValue` | number | **Optional.** Value used to order the document when ordering by parent and child-order is set to manual. |
| `_childOrder` | string | **Optional.** Default ordering of children when calling `findChildren` if no order is given in the query. |

Returns

**object** : ([`Node`](docs/code/stable/fundamentals/types.md#node)) The created node.

Example

Create a node on a repo connection:

```typescript
const result1 = repo.create({
    _name: 'nerd',
    displayName: 'Carpenter and IT expert',
    likes: 'Plywood',
    numberOfUselessGadgets: 123
});
```

Sample response

```typescript
const expected = {
  _id: "2f0d5c09-39fe-4746-9754-74491d75a185",
  _name: "nerd",
  _path: "/nerd",
  _childOrder: "_ts DESC",
  _indexConfig: {
    default: {
      decideByType: true,
      enabled: true,
      nGram: false,
      fulltext: false,
      includeInAllText: false,
      path: false,
      indexValueProcessors: [],
      languages: []
    },
    configs: []
  },
  _permissions: [
    {
      principal: "role:system.admin",
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
    },
    {
      principal: "role:system.everyone",
      allow: [
        "READ"
      ],
      deny: []
    }
  ],
  _state: "DEFAULT",
  _nodeType: "default",
  _versionKey: "aa95ae7e-b975-4879-a19c-cce3b1fc3742",
  _ts: "2021-05-15T08:46:37.227Z",
  displayName: "Carpenter and IT expert",
  likes: "Plywood",
  numberOfUselessGadgets: 123
}
```

Create node with stemmed indices for specific languages

Setting the languages in the node config will create stemmed indices for all mapped properties.

> **Note:** Use [stemmed()](docs/code/stable/storage/noql.md#stemmed) function to query data based on these indices.

```typescript
repo.create({
    _name: "fruits",
    displayName: "Fruit basket",
    description: "language indices usage example",
    english_set: {
      fruit_a: "Apple",
      fruit_set: {
            fruit_b: "Lemon",
            fruit_c: "Orange"
        }
    },
    norwegian_set: {
        fruit_a: "Eple",
        fruit_set: {
            fruit_b: "Sitron",
            fruit_c: "Oransje"
        }
    },
    _indexConfig: {
        default: {
            enabled: true,
            decideByType: true,
            nGram: false,
            fulltext: false,
            includeInAllText: false,
            path: false,
            languages: ['en']
        }, configs: [{
            path: "norwegian_set.**",
            config: {
                enabled: true,
                decideByType: false,
                nGram: true,
                fulltext: true,
                includeInAllText: true,
                path: false,
                languages: ['no']
            }
        }]
    }
});
```

Stemmed english indices will be generated for `displayName`, `description` and all strings inside `english_set`. Norwegian indices will be created for strings inside `norwegian_set` only.

### delete

Deletes a node or nodes.

Parameters

`delete()` is positional. It accepts one or more node keys (ids or paths), where each argument can be a single key or an array of keys. Prefer ids over paths.

Returns

**string[]** : The list of keys that were actually deleted.

Example

Deleting nodes

```typescript
const result = repo.delete('nodeId', '/node2-path', 'missingNodeId');
```

Sample response

```typescript
[
    "7b175b63-b012-4f20-b31d-b8f78420d7f1",
    "69f225a1-e775-4845-89f0-29b808a9a659"
]
```

### diff

Resolves the differences for a node between the branch in the current context and a `target` branch.

Parameters

`diff()` takes a single `DiffBranchesParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id to resolve the diff for. |
| target | string | Branch to differentiate with. |
| includeChildren | boolean | If set to `true`, differences are resolved for all children. |

Returns

**object** : ([DiffBranchesResult](#diff-branches-result)) The status difference for each node in the tree that differs between the branches.

Example

Comparing draft and master branch

```typescript
const result = repo.diff({
    key: '/my-name',
    target: 'draft',
    includeChildren: true
});
```

Sample response

```typescript
{
    diff: [
        {
            id: "c8121875-a9b7-42e4-acf2-75cb52687ddb", (1)
            status: "NEWER"
        }
    ]
}
```

| ****1** | There are 2 children, but only one has been changed |
| --- | --- |

### duplicate

Duplicates a node.

Parameters

`duplicate()` takes a single `DuplicateParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| nodeId | string | Id of the node. |
| name | string | **Optional.** New node name. |
| includeChildren | boolean | **Optional.** Indicates that children nodes must be duplicated, too. Defaults to `true`. |
| parent | string | **Optional.** Destination parent path. By default, a duplicated node is added as a sibling of the source node. |
| refresh | string | **Optional.** Refresh mode for the index of the current connection (`SEARCH`, `STORAGE` or `ALL`). |
| dataProcessor | function | **Optional.** Node data processor callback, receiving the node data and returning the processed data. |

Returns

**object** : ([`Node`](docs/code/stable/fundamentals/types.md#node)) The duplicated node.

Example

Duplicate a node

```typescript
const result = repo.duplicate({
    nodeId: 'nodeId',
    name: 'duplicated-node',
    includeChildren: false,
    dataProcessor: (originalData) => {
        originalData.data.extraProp = 'extraPropValue';
        return originalData;
    },
    parent: '/',
    refresh: 'SEARCH'
});
```

### exists

Checks if a node exists in the current context.

Parameters

`exists()` is positional. It takes a single `key` string — the path or id of the node.

Returns

**boolean** : `true` if the node exists, `false` otherwise.

Examples

Check for existing node by path

```typescript
// Checking if a node exists by path
const result = repo.exists('/path/to/mynode');

if (result) {
    log.info('Node exists');
} else {
    log.info('Node does not exist');
}
```

Check for existing node by id

```typescript
// Checking if a node exists by id
const result = repo.exists('77963d9e-b3c8-4a53-85a9-20c375a92742');

if (result) {
    log.info('Node exists');
} else {
    log.info('Node does not exist');
}
```

### findChildren

Fetches children of a node.

Parameters

`findChildren()` takes a single `FindChildrenParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| parentKey | string | Path or id of the parent to get children of. |
| start | number | **Optional.** Start index used for paging. Defaults to `0`. |
| count | number | **Optional.** Number of nodes to fetch, used for paging. Defaults to `10`. |
| childOrder | string | **Optional.** How to order the children. Defaults to the value stored on the parent. |
| countOnly | boolean | **Optional.** Optimize for counting children only. Defaults to `false`. |
| recursive | boolean | **Optional.** Recursively fetch all children of children. Defaults to `false`. |

Returns

**object** : ([FindNodesByParentResult](#find-nodes-by-parent-result)) Result stats and an array with the ids of the children.

Example

Find child nodes under a given parent path

```typescript
const result = repo.findChildren({
    parentKey: "/my-name"
});
```

Sample response

```typescript
const expected = {
    total: 2,
    count: 10,
    hits: [
        {
            id: "c8121875-a9b7-42e4-acf2-75cb52687ddb"
        },
        {
            id: "636a616b-c8e4-480c-afa9-be88a737cf52"
        }
    ]
}
```

### getVersions

Returns versions of a node.

Parameters

`getVersions()` takes a single `GetVersionsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the node to get versions of. |
| cursor | string | **Optional.** Opaque cursor returned in a previous result, used to fetch the next page. |
| count | number | **Optional.** Number of versions to fetch. Defaults to `10`. |

Returns

**object** : ([GetNodeVersionsResult](#get-node-versions-result)) Result stats, the cursor for the next page (if any), and an array of [NodeVersion](#node-version) entries.

Example

Fetch the first page of versions, then the next page using the returned cursor.

```typescript
const firstPage = repo.getVersions({
    key: '/my-name',
    count: 2
});

if (firstPage.cursor) {
    const nextPage = repo.getVersions({
        key: '/my-name',
        count: 2,
        cursor: firstPage.cursor
    });
}
```

Sample response

```typescript
const expected = {
    total: 40,
    count: 2,
    cursor: "eyJ0cyI6MTAwMDAwMCwiaWQiOiJub2RlVmVyc2lvbk9sZCJ9",
    hits: [
        {
            versionId: "72dcd8c1-9d70-444d-ad7a-508d8c1865a0",
            nodeId: "ddd1c933-0725-45e8-9a54-a3dd87193f60",
            nodePath: "/my-name",
            timestamp: "2019-05-13T15:56:17.018Z"
        },
        {
            versionId: "04c6b8d7-3c56-458f-80c9-c6ee551fc21d",
            nodeId: "ddd1c933-0725-45e8-9a54-a3dd87193f60",
            nodePath: "/my-name",
            timestamp: "2019-05-13T15:56:16.995Z"
        }
    ]
}
```

### get

Fetches a specific node or nodes by path or ID.

Parameters

`get()` is positional. It accepts one or more strings (node ids or paths), one or more arrays of such strings, or one or more `GetNodeParams` objects. Each `GetNodeParams` object has these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Node id or path. |
| versionId | string | **Optional.** Specific version to get the node from. Defaults to the active version. |

Returns

**object** : ([`Node`](docs/code/stable/fundamentals/types.md#node) or `Node[]`) The node, or array of nodes, fetched from the repository. Returns `null` when a single requested node is not found.

Example

Fetch a single node using id as a string.

```typescript
const node = repo.get('nodeId');
```

Fetch several nodes using a sequence of nodeIds.

```typescript
const nodes = repo.get('nodeId_1', 'nodeId_2');
```

Fetch several nodes using an array of nodeIds.

```typescript
const nodes = repo.get(['nodeId_1', 'nodeId_2']);
```

Fetch several nodes using mixed parameters.

```typescript
const nodes = repo.get([{
    key: 'nodeId',
    versionId: 'versionKey'
}, {
    key: '/my-name'
}, 'nodeId']);
```

### getActiveVersion

Returns the active version of a node in the current context branch.

Parameters

`getActiveVersion()` takes a single `GetActiveVersionParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the node. |

Returns

**object** : ([NodeVersion](#node-version)) The active node version, or `null` if the node was not found.

Example

Fetch the active version of a node.

```typescript
const version = repo.getActiveVersion({
    key: '/my-name'
});
```

Sample response

```typescript
const expected = {
    versionId: "72dcd8c1-9d70-444d-ad7a-508d8c1865a0",
    nodeId: "ddd1c933-0725-45e8-9a54-a3dd87193f60",
    nodePath: "/my-name",
    timestamp: "2019-05-13T15:56:17.018Z"
}
```

### getBinary

Returns a binary stream.

Parameters

`getBinary()` takes a single `GetBinaryParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the node. |
| binaryReference | string | **Optional.** Reference to the binary. |

Returns

**object** : ([ByteSource](docs/code/stable/fundamentals/types.md#byte-source)) Stream of the binary.

Example

Fetching the binary of a node.

```typescript
const binaryStream = repo.getBinary({
    key: "/myNode",
    binaryReference: "myBinaryReference"
});
```

### getCommit

Returns a node version commit.

Parameters

`getCommit()` takes a single `GetCommitParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Id of the commit. |

Returns

**object** : ([NodeCommit](#node-commit)) The commit, or `null` if not found.

Example

Fetching a commit version of a node.

```typescript
const commit = repo.getCommit({
    id: "aa1f76bf-4bb9-41be-b166-03561c1555b2"
});
```

Sample response

```typescript
const expected = {
    id: "aa1f76bf-4bb9-41be-b166-03561c1555b2",
    message: "",
    committer: "user:system:anonymous",
    timestamp: "2019-01-24T15:16:36.260799Z"
}
```

### update

Updates a node.

Parameters

`update()` takes a single `UpdateNodeParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the node. |
| editor | function | Editor callback that receives the node and returns the modified node. |

Returns

**object** : ([`Node`](docs/code/stable/fundamentals/types.md#node)) The modified node.

Example

Updating a node.

```typescript
const result = repo.update({
    key: key,
    editor: (node) => {
        node.someData.cars.push('peugeot');
        return node;
    }
});
```

### patch

Applies a patch to a node.

> **Warning:** This is a low-level function. It should be used with caution as it can corrupt data if used incorrectly.

Parameters

`patch()` takes a single `PatchNodeParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the node. |
| editor | function | Patcher callback that receives the node and returns the patched node. |
| branches | string[] | **Optional.** A list of branches to patch. Defaults to `[]`.    * If not provided or empty, the node in the current context branch will be patched.    * If one branch is listed, the patch occurs in that specific branch.    * If multiple branches are listed:    1. The patch is applied to the **first** branch in the list.    2. For each subsequent branch in the list:    * If its node version is identical to the **original** (pre-patch) version from any processed branch, it is simply switched to point to the new, patched version. (`publish` permission is required)    * If its node version is **different**, the patch is applied to it separately (`update` permission is required). |

Returns

**object** : ([PatchNodeResult](#patch-node-result)) Patch result, with one entry in `branchResults` per branch where the node was patched.

**Patchable Fields:**

| Name | Type | Description |
| --- | --- | --- |
| displayName | string | The display name of the node. |
| `_nodeType` | string | The type definition of the node. |
| `_indexConfig` | object | An object defining the search [index](docs/code/stable/storage/indexing.md) configuration for this node. |
| `_childOrder` | string | Defines the default sort order for the node’s direct children. |
| `_manualOrderValue` | number | Numeric value used for manual sorting among siblings (when the parent’s `_childOrder` is manual). |

Any data can also be patched if the name of the field does not start with an underscore (`_`).

Examples

Patching a node’s display name and adding a new field.

```typescript
const patchedNode = repo.patch({
    key: '/my-node',
    editor: (node) => {
        node.displayName = 'New Display Name';
        node.newField = 'New Value';
        return node;
    }
});
```

Patching childOrder in multiple branches.

```typescript
const patchedNode = repo.patch({
    key: '/my-node',
    branches: ['master', 'draft', 'other'],
    editor: (node) => {
        node._childOrder = 'field DESC';
        return node;
    }
});
```

Patching a node with data stream.

```typescript
var ioLib = require('/lib/xp/io');

var stream = ioLib.newStream('Hello World');

const patchedNode = repo.patch({
    key: '/my-node',
    editor: (node) => {
        node.attachmentField = {
            data: stream
        };
        return node;
    }
});
```

### move

Renames a node or moves it to a new path.

Parameters

`move()` takes a single `MoveNodeParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| source | string | Path or id of the node to be moved or renamed. |
| target | string | New path or name for the node. If the target ends in slash `/`, it specifies the parent path to move the node under. Otherwise it is the new desired path or name for the node. |

Returns

**object** : ([`Node`](docs/code/stable/fundamentals/types.md#node)) The moved or renamed node.

Examples

Changing the name of a node.

```typescript
const moved = repo.move({
    source: '/my-name',
    target: 'new-name'
});
```

Moving a node to a new location.

```typescript
const moved = repo.move({
    source: '/my-name',
    target: '/new-parent/'
});
```

Move and rename a node in the same operation.

```typescript
const moved = repo.move({
    source: '/my-name',
    target: '/content/my-site/folder/new-name'
});
```

### push

Pushes a node to a given branch.

Parameters

`push()` takes a single `PushNodeParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| target | string | Branch to push to. |
| key | string | **Optional.** Id or path of the node. Provide either `key` or `keys`. |
| keys | string[] | **Optional.** Array of ids or paths of the nodes. Provide either `key` or `keys`. |
| includeChildren | boolean | **Optional.** Also push children of the given nodes. Defaults to `false`. |
| resolve | boolean | **Optional.** Resolve dependencies before pushing, meaning that references are also pushed. Defaults to `true`. |
| exclude | string[] | **Optional.** Array of ids or paths of nodes not to be pushed. If using this, be aware that nodes need to maintain data integrity (e.g. parents must be present in the target). If data integrity is not maintained with excluded nodes, they will be pushed anyway. |

Returns

**object** : ([PushNodesResult](#push-nodes-result)) Lists the keys that were pushed and any that failed.

Examples

Pushing nodes from current branch.

```typescript
const result = repo.push({
    keys: ['a'],
    target: 'otherBranch',
    resolve: false
});
```

Sample response

```typescript
const expected = {
    success: [
        "a"
    ],
    failed: []
}
```

Pushing content with children where not all children are allowed.

```typescript
const result = repo.push({
    keys: ['a'],
    target: 'otherBranch',
    resolve: true,
    includeChildren: true
});
```

Sample response

```typescript
const expected = {
    success: [
        "a",
        "b",
        "c"
    ],
    failed: [
        {
            id: "d",
            reason: "ACCESS_DENIED"
        }
    ]
}
```

Pushing node with children, but excluding some of them.

```typescript
const result = repo.push({
    keys: ['/a'],
    target: 'otherBranch',
    resolve: true,
    includeChildren: true,
    exclude: ['/a/b', '/a/c']
});
```

Sample response

```typescript
const expected = {
    success: [
        "a",
        "d"
    ],
    failed: []
}
```

### query

Queries nodes.

Parameters

`query()` takes a single `QueryNodeParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| query | string/object | **Optional.** Query string or [DSL](docs/code/stable/storage/querying.md) expression. |
| start | number | **Optional.** Start index used for paging. Defaults to `0`. |
| count | number | **Optional.** Number of nodes to fetch, used for paging. Defaults to `10`. |
| filters | object | **Optional.** Query filters. |
| sort | string/object | **Optional.** Sorting string or [DSL](docs/code/stable/storage/querying.md#sort) expression. Defaults to `_score DESC`. |
| aggregations | object | **Optional.** [Aggregations](docs/code/stable/storage/aggregations.md) config. |
| highlight | object | **Optional.** [Highlighting](docs/code/stable/storage/highlighting.md) config. |
| suggestions | object | **Optional.** Term suggestions config, keyed by suggestion name. |
| explain | boolean | **Optional.** If set to `true`, score calculation explanation will be included in result. |

Returns

**object** : ([NodeQueryResult](#node-query-result)) Result stats, hits and, if requested, aggregations.

Examples

A simple query using the fulltext function

```typescript
const result = repo.query({
    query: "fulltext('_name', '_name')"
});
```

Sample response

```typescript
const expected = {
    total: 4,
    count: 4,
    hits: [
        {
            id: "5be12847-cbad-4e61-a36c-e94ffb597afb",
            score: 0.7071067690849304
        },
        {
            id: "3928476f-915d-4a6a-97cc-f1c8a905f71a",
            score: 0.625
        },
        {
            id: "a2e38aab-6efb-4f20-862c-e23ef24b3fc3",
            score: 0.5
        },
        {
            id: "3a842eff-ef49-4781-8c1a-dcfcf515db51",
            score: 0.5
        }
    ],
    aggregations: {}
}
```

Query content using aggregations.

```typescript
const result = repo.query({
    start: 0,
    count: 2,
    query: "startTime > instant('2016-10-11T14:38:54.454Z')",
    filters: {
        boolean: {
            must: [
                {
                    exists: {
                        field: "modifiedTime"
                    }
                },
                {
                    exists: {
                        field: "other"
                    }
                }
            ],
            mustNot: {
                hasValue: {
                    field: "myField",
                    values: [
                        "cheese",
                        "fish",
                        "onion"
                    ]
                }
            }
        },
        notExists: {
            field: "unwantedField"
        },
        ids: {
            values: ["id1", "id2"]
        }
    },
    sort: "duration DESC",
    aggregations: {
        urls: {
            terms: {
                field: "url",
                order: "_count desc",
                size: 2
            },
            aggregations: {
                duration: {
                    histogram: {
                        field: "duration",
                        interval: 100,
                        minDocCount: 1,
                        extendedBoundMin: 0,
                        extendedBoundMax: 10000,
                        order: "_key desc"
                    }
                },
                durationStats: {
                    stats: {
                        field: "duration"
                    }
                }
            }
        }
    }
});
```

Sample response

```typescript
const expected = {
    total: 12902,
    count: 2,
    hits: [
        {
            id: "b186d24f-ac38-42ca-a6db-1c1bda6c6c26",
            score: 1.2300000190734863
        },
        {
            id: "350ba4a6-589c-498b-8af0-f183850e1120",
            score: 1.399999976158142
        }
    ],
    aggregations: {
        urls: {
            buckets: [
                {
                    key: "/site/draft/superhero/search",
                    docCount: 6762,
                    duration: {
                        buckets: [
                            {
                                key: "1600",
                                docCount: 2
                            },
                            {
                                key: "1400",
                                docCount: 1
                            },
                            {
                                key: "1300",
                                docCount: 5
                            }
                        ]
                    }
                },
                {
                    key: "/site/draft/superhero",
                    docCount: 1245,
                    duration: {
                        buckets: [
                            {
                                key: "1600",
                                docCount: 2
                            },
                            {
                                key: "1400",
                                docCount: 1
                            },
                            {
                                key: "1300",
                                docCount: 5
                            }
                        ]
                    }
                }
            ]
        }
    }
}
```

Query node using stemmed DSL function for specific language.

```typescript
const result = repo.query({
    query: {
        stemmed: {
            field: "description",
            value: "running",
            language: "en"
        }
    }
});
```

Sample response

```typescript
const expected = {
    total: 1,
    count: 1,
    hits: [
        {
            id: "2f0d5c09-39fe-4746-9756-74491d75a185",
            score: 0.5
        }
    ],
    aggregations: {}
}
```

### refresh

Refreshes indices for the current connection. The index has two parts: search and storage. It is possible to refresh both or just one of them.

Parameters

`refresh()` is positional. It takes an optional `mode` string: `ALL` for both indices, `SEARCH` for the search index or `STORAGE` for the storage index. Defaults to `ALL`.

Returns

Nothing.

Examples

Refreshing the full index

```typescript
repo.refresh();
```

Refreshing the serach index

```typescript
repo.refresh('SEARCH');
```

### sort

Sorts the children of a node by changing the parent’s `_childOrder`. When the parent is set to manual ordering, child nodes are reordered according to their `_manualOrderValue`.

Parameters

`sort()` takes a single `SortNodeParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the parent node. |
| childOrder | string | New child order expression for the parent (for example `displayName ASC` or `_manualOrderValue DESC`). |

Returns

**object** : ([SortNodeResult](#sort-node-result)) The updated parent `node` and an array of `reorderedNodes` describing children whose ordering was affected.

Example

Setting the children to be ordered in reverse alphabetical order by name

```typescript
const result = repo.sort({
    key: '/name-list',
    childOrder: 'name DESC'
});
```

### applyPermissions

Applies permissions on a node.

Parameters

`applyPermissions()` takes a single `ApplyPermissionsParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| key | string | Path or id of the node. |
| permissions | [AccessControlEntry](#access-control-entry)[] | **Optional.** Array of permissions to overwrite current permissions. Cannot be combined with `addPermissions` or `removePermissions`. |
| addPermissions | [AccessControlEntry](#access-control-entry)[] | **Optional.** Array of permissions to add. Cannot be combined with `permissions`. |
| removePermissions | [AccessControlEntry](#access-control-entry)[] | **Optional.** Array of permissions to remove. Cannot be combined with `permissions`. |
| scope | string | **Optional.** Scope of applying permissions. `SINGLE` applies permissions only to the node itself. `TREE` applies permissions to the node and its descendants. `SUBTREE` applies permissions only to the node’s descendants. Defaults to `SINGLE`. |
| branches | string[] | **Optional.** Array of additional branches to apply permissions to. The current context branch should not be included. |

Returns

**object** : ([ApplyPermissionsResult](#apply-permissions-result)) An object keyed by node id, with one `branchResults` entry per branch the permissions were applied to.

Examples

1) Applying permissions to a node by overwriting the current permissions.

```typescript
repo.applyPermissions({
    key: '/my-node',
    permissions: [
        {
            principal: 'role:system.everyone',
            allow: ['READ']
        },
        {
            principal: 'user:system:my-user',
            allow: ['READ', 'CREATE', 'MODIFY', 'DELETE']
        }
    ]
});
```

2) Adding permissions to a node.

```typescript
repo.applyPermissions({
    key: '/my-node',
    addPermissions: [
        {
            principal: 'role:system.everyone',
            allow: ['CREATE', 'MODIFY']  // 'READ' permission is already set and will be kept.
        },
        {
            principal: 'user:system:my-new-user',
            allow: ['READ', 'CREATE', 'MODIFY', 'DELETE'] // New user will have all permissions.
        }
    ]
});
```

3) Removing permissions from a node.

```typescript
repo.applyPermissions({
    key: '/my-node',
    removePermissions: [
        {
            principal: 'role:system.everyone',
            allow: ['CREATE', 'MODIFY']  // 'READ' permission will be kept.
        },
        {
            principal: 'user:system:my-user',
            allow: ['DELETE'] // 'DELETE' permission will be removed. All other permissions will be kept.
        },
        {
            principal: 'user:system:my-new-user' // All permissions for this principal will be removed.
        }
    ]
});
```

Applying permissions to a node and its descendants.

```typescript
repo.applyPermissions({
    key: '/my-node',
    permissions: [
        {
            principal: 'role:system.everyone',
            allow: ['READ']
        }
    ],
    scope: 'TREE'
});
```

Applying permissions to a node’s descendants only.

```typescript
repo.applyPermissions({
    key: '/my-node',
    permissions: [
        {
            principal: 'role:system.everyone',
            allow: ['READ']
        }
    ],
    scope: 'SUBTREE'
});
```

Applying permissions to a node and its descendants in multiple branches.

```typescript
repo.applyPermissions({
    key: '/my-node',
    permissions: [
        {
            principal: 'role:system.everyone',
            allow: ['READ']
        }
    ],
    scope: 'TREE',
    branches: ['branch1', 'branch2']
});
```

## Type Definitions

### ConnectParams

Properties

| Name | Type | Description |
| --- | --- | --- |
| repoId | string | Repository ID. |
| branch | string | Branch ID. |
| principals | [PrincipalKey](docs/code/stable/fundamentals/types.md#principal-key)[] | **Optional.** Additional principals to execute the connection with. |
| user | [ConnectUser](#connect-user) | **Optional.** User to execute the connection as. Defaults to the current user. Not allowed when this source is part of a `multiRepoConnect` call. |

### ConnectUser

Properties

| Name | Type | Description |
| --- | --- | --- |
| login | string | User id of the user. |
| idProvider | string | **Optional.** Id provider containing the user. Defaults to the `system` provider. |

### NodeCommit

Properties

| Name | Type | Description |
| --- | --- | --- |
| id | string | Commit id. |
| message | string | Commit message. |
| committer | string | Principal key of the commit creator. |
| timestamp | string | Time of creation. |

### NodeVersion

Properties

| Name | Type | Description |
| --- | --- | --- |
| versionId | string | Version id. |
| nodeId | string | Node id. |
| nodePath | string | Node path. |
| timestamp | string | Time of the version. |
| commitId | string | **Optional.** Id of the commit this version belongs to. |

### AccessControlEntry

Properties

| Name | Type | Description |
| --- | --- | --- |
| principal | [PrincipalKey](docs/code/stable/fundamentals/types.md#principal-key) | Principal key (for example `role:system.everyone` or `user:system:my-user`). |
| allow | string[] | **Optional.** Permissions to allow. Possible values are `READ`, `CREATE`, `MODIFY`, `DELETE`, `PUBLISH`, `READ_PERMISSIONS` and `WRITE_PERMISSIONS`. |
| deny | string[] | **Optional.** Permissions to deny. Same possible values as `allow`. |

### NodeQueryResult

Properties

| Name | Type | Description |
| --- | --- | --- |
| total | number | Total number of nodes matching the query. |
| count | number | Number of hits returned in this result. |
| hits | object[] | Array of hits, each with an `id` and a `score` (and optionally `explanation` and `highlight`). |
| aggregations | object | Aggregations result, when aggregations were requested. |
| suggestions | object | **Optional.** Suggestions result, when suggestions were requested. |

### NodeMultiRepoQueryResult

Properties

Same shape as [NodeQueryResult](#node-query-result), except each hit also carries the `repoId` and `branch` it came from.

| Name | Type | Description |
| --- | --- | --- |
| total | number | Total number of nodes matching the query. |
| count | number | Number of hits returned in this result. |
| hits | object[] | Array of hits, each with `id`, `score`, `repoId` and `branch` (and optionally `explanation` and `highlight`). |
| aggregations | object | Aggregations result, when aggregations were requested. |
| suggestions | object | **Optional.** Suggestions result, when suggestions were requested. |

### FindNodesByParentResult

Properties

| Name | Type | Description |
| --- | --- | --- |
| total | number | Total number of children. |
| count | number | Number of hits returned in this result. |
| hits | object[] | Array of hits, each with an `id`. |

### GetNodeVersionsResult

Properties

| Name | Type | Description |
| --- | --- | --- |
| total | number | Total number of versions. |
| count | number | Number of hits returned in this result. |
| cursor | string | **Optional.** Cursor used to fetch the next page, when more results are available. |
| hits | [NodeVersion](#node-version)[] | Array of node versions. |

### DiffBranchesResult

Properties

| Name | Type | Description |
| --- | --- | --- |
| diff | object[] | Array of entries, each with an `id` and a `status` describing how the node differs between the branches. |

### PushNodesResult

Properties

| Name | Type | Description |
| --- | --- | --- |
| success | string[] | Keys of the nodes that were successfully pushed. |
| failed | object[] | Array of entries, each with an `id` and a `reason`, for nodes that could not be pushed. |

### SortNodeResult

Properties

| Name | Type | Description |
| --- | --- | --- |
| node | object | ([`Node`](docs/code/stable/fundamentals/types.md#node)) The parent node after the new child order was applied. |
| reorderedNodes | object[] | Array of entries, each with a `node`, describing the children whose ordering was affected. |

### PatchNodeResult

Properties

| Name | Type | Description |
| --- | --- | --- |
| branchResults | object[] | Array of entries, each with a `branch` and the patched `node`, one per branch where the node was patched. |

### ApplyPermissionsResult

Properties

An object keyed by node id. Each value has a single `branchResults` property — an array of entries, each with a `branch` and the resulting `permissions` ([AccessControlEntry](#access-control-entry)[]) applied in that branch.
