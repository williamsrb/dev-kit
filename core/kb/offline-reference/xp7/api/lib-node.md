<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-node generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-node.md

# Node API

This API provides functions to get, query and manipulate nodes.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-node:${xpVersion}"
}
```

Add the `import` statement to your controller:

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

For information on events, check out the [event API](/docs/platform/7.x/api/lib-event)

## Functions

### connect

Creates a connection to a repository with a given branch and authentication info.

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| params | [Source](#source) | object with paramters |

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

| Name | Kind | Details |
| --- | --- | --- |
| sources | [Source](#source)[] | array of repository source objects |

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

An object with the following keys and their values:

| Name | Type | Attributes | Details |
| --- | --- | --- | --- |
| start | number | optional | Start index used for paging - default: 0 |
| count | number | optional | Number of content to fetch, used for paging - default: 10 |
| query | string/object |  | Query string or [DSL](/docs/platform/7.x/storage/dsl) expression. |
| filters | object | optional | Query filters |
| sort | string | optional | Sorting expression - default: '_score DESC' |
| aggregations | object | optional | [Aggregations](/docs/platform/7.x/storage/aggregations) config |
| highlight | object | optional | [Highlighting](/docs/platform/7.x/storage/highlighting) config |
| explain | boolean | optional | If set to `true`, score calculation explanation will be included in result. |

Returns

**object** : Result of query

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

| Name | Kind | Details |
| --- | --- | --- |
| keys | string \| string[] | Node keys to commit. Each argument could be an id, a path or an array of the two. Prefer the usage of ID rather than paths. |
| message | string | Optional commit message |

Returns

**object** : Commit object(s)

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
    {
        id: "aa1f76bf-4bb9-41be-b166-03561c1555b2",
        message: "Commit message",
        committer: "user:system:anonymous",
        timestamp: "2019-01-24T15:19:30.818029Z"
    },
    {
        id: "5c15b187-e3ab-4d87-88b2-ffb84bd1c7bb",
        message: "Commit message",
        committer: "user:system:anonymous",
        timestamp: "2019-01-24T15:19:30.818029Z"
    }
}
```

### create

Creates a node. To create a content where the name is not important and there could be multiple instances under the same parent content, skip the `name` parameter and specify a `displayName`.

Parameters

An object with the following keys and their values:

| Name | Type | Attributes | Details |
| --- | --- | --- | --- |
| _name | string | <optional> | Name of content. |
| _parentPath | string | <optional> | Path to place content under. |
| _indexConfig | object | <optional> | How the document should be [indexed](/docs/platform/7.x/storage/indexing). A default template value "[byType](/docs/platform/7.x/storage/indexing#byType)" will be set if no value specified. |
| _permissions | object | <optional> | The access control list for the node. By default the creator will have full access |
| _inheritsPermissions | boolean | <optional> | `true` if the permissions should be inherited from the node parent. Default is `false`. |
| _manualOrderValue | number | <optional> | Value used to order document when ordering by parent and child-order is set to manual |
| _childOrder | string | <optional> | Default ordering of children when doing getChildren if no order is given in query |

Returns

**object** : Created object

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
  _inheritsPermissions: false,
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

> **Note:** Use [stemmed()](noql.ahtml#stemmed) function to query data based on these indices.

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

| Name | Kind | Details |
| --- | --- | --- |
| keys | string \| string[] | Node keys to delete. Each argument could be an id, a path or an array of the two. Prefer the usage of ID rather than paths. |

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

An object with the following keys and their values:

| Name | Type | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Path or id to resolve diff for |
| target | string |  | Branch to differentiate with |
| includeChildren | boolean | optional | If set to `true`, differences are resolved for all children. |

Returns

**object** : An array with differences in the status for each node in the tree that has differences between the branches.

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

XP 7.12.0 Duplicates a node.

Parameters

An object with the following keys and their values:

| Name | Kind | Attributes | Default | Details |
| --- | --- | --- | --- | --- |
| nodeId | string |  |  | Id to the node. |
| name | string | <optional> |  | New node name. |
| includeChildren | boolean | <optional> | true | Indicates that children nodes must be duplicated, too. |
| parent | string | <optional> |  | Destination parent path. By default, a duplicated node will be added as a sibling of the source node. |
| refresh | string | <optional> |  | Refresh the index for the current repoConnection. |
| dataProcessor | function | <optional> |  | Node data processor. |

Returns duplicated node.

**object** : Duplicated node

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

| Name | Kind | Details |
| --- | --- | --- |
| key | string | Path or id to the node |

Returns

**boolean** : `true` if exists, `false` otherwise

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

An object with the following keys and their values:

| Name | Type | Attributes | Details |
| --- | --- | --- | --- |
| parentKey | string |  | Path or ID of parent to get children of |
| start | number | optional | start index used for paging - default: 0 |
| count | number | optional | number of content to fetch, used for paging - default: 10 |
| childOrder | string | optional | How to order the children - default is value stored on parent |
| countOnly | boolean | optional | Optimize for count children only - default is `false` |
| recursive | boolean | optional | Do recursive fetching of all children of children - default is `false` |

Returns

**object** : An object with stats about the result and an array with all IDs of the children.

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

### findVersions

Fetches versions of a node.

Parameters

An object with the following keys and their values:

| Name | Type | Attributes | Details |
| --- | --- | --- | --- |
| key | string |  | Path or ID of a node to get versions of |
| start | number | optional | start index used for paging - default: 0 |
| count | number | optional | number of content to fetch, used for paging - default: 10 |

Returns

**object** : An object with stats about the result and an array listing the versions

Example

Fetch all versions of a content with a given path

```typescript
const result = repo.findVersions({
    key: '/my-name'
});
```

Sample response

```typescript
const expected = {
    total: 2,
    count: 2,
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

| Name | Kind | Details |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| params | string \| string[]\|object | One or multiple strings, or one or multiple arrays of strings, or an object with the following properties:      Properties                    Name | Type | Attributes | Default | Description |
| key | string |  |  | Node id or path |  |  |
| versionId | string | <optional> |  | Specific version to get the node from (default is active version) |  |  |

Returns

**object** : The node or node array (as JSON) fetched from the repository.

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

Fetches the active version of a node.

Parameters

An object with the following key and value:

| Name | Kind | Details |
| --- | --- | --- |
| key | string | Path or ID of the node |

Returns

**object** : Active content versions per branch

### getBinary

Returns a binary stream.

Parameters

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| key | string | Path or ID of the node |
| binaryReference | string | to the binary |

Returns

**\*** : Stream of the binary

Example

Fetching the binary of a node.

```typescript
const binaryStream = repo.getBinary({
    key: "/myNode",
    binaryReference: "myBinaryReference"
});
```

### getCommit

XP 7.7.0

Returns a node version commit.

Parameters

An object with the following keys and their value:

| Name | Kind | Details |
| --- | --- | --- |
| id | string | ID of the commit |

Returns

**object** : Commit object

| Name | Kind | Details |
| --- | --- | --- |
| id | string | Commit ID |
| message | string | Optional commit message |
| committer | string | Principal key of commit creator |
| timestamp | string | Time of creation |

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

### modify

Modifies a node.

Parameters

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| key | string | Path or ID of the node |
| editor | function | Editor callback function |

Returns

**object** : The modified node

Example

Modifying a node.

```typescript
const result = repo.modify({
    key: key,
    editor: (node) => {
        node.someData.cars.push('peugeot');
        return node;
    }
});
```

### move

Renames a node or moves it to a new path.

Parameters

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| source | string | Path or id of the node to be moved or renamed |
| target | string | New path or name for the node. If the target ends in slash '/', it specifies the parent path where to be moved. Otherwise it means the new desired path or name for the node. |

Returns

**boolean** : `true` if the node was successfully moved or renamed, `false` otherwise.

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

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| key | string | Id or path to the nodes |
| keys | string[] | Array of ids or paths to the nodes |
| target | string | Branch to push to |
| includeChildren | boolean | Also push children of given nodes. Default is `false`. |
| resolve | boolean | Resolve dependencies before pushing, meaning that references will also be pushed. Default is `true`. |
| exclude | string[] | Optional array of ids or paths to nodes not to be pushed. If using this, be aware that nodes need to maintain data integrity (e.g parents must be present in target). If data integrity is not maintained with excluded nodes, they will be pushed anyway. |

Returns

**object** : PushNodeResult

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
    failed: [],
    deleted: []
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
const expected ={
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
    ],
    deleted: []
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
    failed: [],
    deleted: []
}
```

### query

Queries nodes

Parameters

An object with the following keys and their values:

| Name | Type | Attributes | Details |
| --- | --- | --- | --- |
| start | number | optional | Start index used for paging - default: 0 |
| count | number | optional | Number of content to fetch, used for paging - default: 10 |
| query | string/object |  | Query string or [DSL](/docs/platform/7.x/storage/dsl) expression. |
| filters | object | optional | Query filters |
| sort | string/object | optional | Sorting string or [DSL](/docs/platform/7.x/storage/dsl#sort) expression. Default: '_score DESC' |
| aggregations | object | optional | [Aggregations](/docs/platform/7.x/storage/aggregations) config |
| highlight | object | optional | [Highlighting](/docs/platform/7.x/storage/highlighting) config |
| explain | boolean | optional | If set to `true`, score calculation explanation will be included in result. |

Returns

**object** : stats, hits and if requested, aggregations

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

### refresh

Refreshes indices for the current repoConnection. The index has two parts: search and storage. It is possible to index both or just one of them.

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| mode | string | ALL for both indices, SEARCH for search-index or STORAGE for storage-index. Default is ALL. |

Returns

**NULL**

Examples

Refreshing the full index

```typescript
repo.refresh();
```

Refreshing the serach index

```typescript
repo.refresh('SEARCH');
```

### setActiveVersion

Sets the active version of a node.

Parameters

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| key | string | Path or ID of the node |
| versionID | string | Version to set as active |

Returns

**boolean** : `true` if deleted, `false` otherwise

Example

Setting the previous version active

```typescript
const findVersions = repo.findVersions({
    key: node._id
});

const result = repo.setActiveVersion({
    key: node._id,
    versionId: findVersions.hits[1].versionId
});
```

### setChildOrder

Sets the order of a node’s children.

Parameters

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| key | string | Path or ID of the node |
| childOrder | string | children order |

Returns

**object** : The updated node

Example

Setting the children to be ordered in reverse alphabetical order by name

```typescript
repo.setChildOrder({
    key: '/name-list',
    childOrder: 'name DESC'
});
```

### setRootPermissions

Sets the root node’s permissions and inheritance.

Parameters

An object with the following keys and their values:

| Name | Kind | Details |
| --- | --- | --- |
| _permissions | object | The permissions |
| _inheritPermissions | boolean | `true` if the permissions should be inherited to children |

Returns

**object** : The updated root-node

Example

Setting example permissions

```typescript
const result = repo.setRootPermissions({
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
        }
    ],
    _inheritsPermissions: true
});
```

## Source

A source definition of repositories:

Fields

| Name | Kind | Details |
| --- | --- | --- |
| repoId | object | Repository ID |
| branch | object | Branch ID |
| user | [User](#user) | Optional user to execute the callback with - Default is the default user |
| principals | string[] | Additional principals to execute the callback with |

## User

User object to use for connections:

Fields

| Name | Kind | Details |
| --- | --- | --- |
| login | string | user ID of the user |
| idProvider | string | Optional ID provider containing the user. By default, all the id providers will be used. |
