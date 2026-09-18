<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-export generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-export.md

# Export library

This API provides functions for creating and importing node-exports.

## Usage

```groovy
dependencies {
  include xplibs.export
}
```

```typescript
import exportLib from '/lib/xp/export';
```

## Functions

### exportNodes

Creates a node export.

Parameters

`exportNodes()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| sourceNodePath | string | Source nodes path. |
| exportName | string | Export name. |
| nodeResolved | function | **Optional.** A function to be called before export starts with the number of nodes to export. |
| nodeExported | function | **Optional.** A function to be called during export with the number of nodes exported since the last call. |
| batchSize | number | **Optional.** Controls how many nodes are loaded into memory simultaneously during export. A higher value may speed up export but also increase memory usage. Defaults to `1000`. |

Returns

**object** : Node export results

Examples

```typescript
import {exportNodes} from '/lib/xp/export';

// Export content nodes.
const result = exportNodes({
    sourceNodePath: '/content',
    exportName: 'export-1',
    nodeExported: (i: number) => {
    },
    nodeResolved: (i: number) => {
    }
});
```

```typescript
import {exportNodes} from '/lib/xp/export';

// Export content nodes with a custom batch size.
const result = exportNodes({
    sourceNodePath: '/content',
    exportName: 'export-batch',
    batchSize: 25
});
```

```typescript
// Information about exported nodes.
const expected = {
    exportedNodes: [
        '/content'
    ],
    exportedBinaries: [
        'binaryPath [ref]'
    ],
    exportErrors: [
        'some error'
    ]
};
```

### importNodes

Imports nodes from a node export or from application resource files. Optionally pre-transforms node XML node files with XSLT before import.

> **Note:** During node export, current permissions are included in the export file. But when importing, you may need to apply permissions according to your new environment/parent permissions. `includePermissions` parameter is used to control this behavior.

Parameters

`importNodes()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| source | string or object | Either the name of a nodes-export located in the exports directory, or an application resource key. |
| targetNodePath | string | Target path for imported nodes. |
| xslt | string or object | **Optional.** XSLT file name in the exports directory or application resource key. Used for XSLT transformation. |
| xsltParams | object | **Optional.** Parameters used in XSLT transformation. |
| includeNodeIds | boolean | **Optional.** Set to `true` to use node IDs from the import, `false` to generate new node IDs. Defaults to `false`. |
| includePermissions | boolean | **Optional.** Set to `true` to overwrite node permissions with permissions from the import, `false` to merge permissions with new parent permissions. Defaults to `false`. |
| versionAttributes | object | **Optional.** Attributes attached to the node version of every imported node. |
| nodeResolved | function | **Optional.** A function to be called before import starts with the number of nodes to import. |
| nodeImported | function | **Optional.** A function to be called during import with the number of nodes imported since the last call. |
| nodeSkipped | function | **Optional.** A function to be called during import with the number of nodes skipped since the last call. |

Returns

**object** : Node import results

Examples

```typescript
import {importNodes} from '/lib/xp/export';

// Import from application resource files
const importedNodes = importNodes({
    source: resolve('/import'),
    targetNodePath: '/content',
    xslt: 'transform.xslt',
    xsltParams: {k: 'v'},
    includeNodeIds: true,
    includePermissions: true,
    nodeImported: (i: number) => {
    },
    nodeResolved: (i: number) => {
    },
    nodeSkipped: (i: number) => {
    }
});
```

```typescript
import {importNodes} from '/lib/xp/export';

// Import from an export in exports directory
const importedNodes = importNodes({
    source: 'export-1',
    targetNodePath: '/content'
});
```

```typescript
// Information about imported nodes.
const expected = {
    addedNodes: [
        '/added'
    ],
    updatedNodes: [
        '/updated'
    ],
    skippedNodes: [],
    importedBinaries: [
        'binaryPath [ref]'
    ],
    importErrors: [
        {
            exception: 'com.enonic.xp.lib.export.ImportHandlerTest$NoStacktraceException',
            message: 'error',
            stacktrace: []
        }
    ]
};
```

### list

Lists the available node exports.

Parameters

None.

Returns

**object** : `{ exports: [{ name: string }] }` — names of all available exports.

Example

```typescript
import {list} from '/lib/xp/export';

const result = list();
// result.exports === [{ name: 'export-1' }, { name: 'export-2' }]
```
