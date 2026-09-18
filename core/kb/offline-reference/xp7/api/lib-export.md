<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-export generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-export.md

# Export API

XP 7.8.0

This API provides functions for creating and importing node-exports.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-export:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import exportLib from '/lib/xp/export';
```

## Functions

### exportNodes

Creates a node export. Export will be created in [exports](/docs/platform/7.x/deployment/config#_export) directory.

Parameters

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| sourceNodePath | string |  |  | Source nodes path |
| exportName | string |  |  | Export name |
| includeNodeIds | boolean | <optional> | true | Set to true to export node IDs |
| includeVersions | boolean | <optional> | false | Set to true to export all node versions |
| nodeResolved | function | <optional> |  | A function to be called before export starts with number of nodes to export |
| nodeExported | function | <optional> |  | A function to be called during export with number of nodes exported since last call |

Returns

**object** : Node export results

Examples

```typescript
import {exportNodes} from '/lib/xp/export';

// Export content nodes.
const exportNodes = exportNodes({
    sourceNodePath: '/content',
    exportName: 'export-1',
    includeNodeIds: true,
    includeVersions: true,
    nodeExported: (i) => {
    },
    nodeResolved: (i) => {
    }
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

Imports nodes from a node export located in [exports](/docs/platform/7.x/deployment/config#_export) directory or from application resource files. Optionally pre-transforms node XML node files with XSLT before import.

Parameters

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| source | string or object |  |  | Either name of nodes-export located in exports directory or application resource key |
| targetNodePath | string |  |  | Target path for imported nodes |
| xslt | string or object | <optional> | true | XSLT file name in exports directory or application resource key. Used for XSLT transformation |
| xsltParams | object | <optional> |  | Parameters used in XSLT transformation |
| includeNodeIds | boolean | <optional> | false | Set to true to use node IDs from the import, false to generate new node IDs |
| includePermissions | boolean | <optional> | false | Set to true to use Node permissions from the import, false to use target node permissions |
| nodeResolved | function | <optional> |  | A function to be called during import with number of nodes imported since last call |
| nodeImported | function | <optional> |  | A function to be called during import with number of nodes imported since last call |

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
    nodeImported: (i) => {
    },
    nodeResolved: (i) => {
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
