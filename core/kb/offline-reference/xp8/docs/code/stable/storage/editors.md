<!-- src:https://developer.enonic.com/docs/code/stable/storage/editors generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/storage/editors.md

# Editors

Where traditional databases use update statements, XP uses **editors**: a function that receives one node (or content) as input and returns the modified version. The engine then writes the result as a new version.

This separates **reading and querying** from **writing**, in the spirit of Command Query Responsibility Segregation (CQRS). It also gives editors a few properties that update statements don’t have:

- **Atomic per node.** Each editor call is a read-modify-write that runs inside the engine — your code never holds a stale snapshot.

- **Delta-shaped.** You describe what changes on the node in front of you, not the full object to persist.

- **Composable with queries.** Run a query, then map over the hits with an editor — the natural pattern for bulk changes.

- **Versioned.** Every editor run produces a new node version; the previous version is preserved.

## Anatomy

An editor is a plain function:

```typescript
(node) => {
    // mutate node in place, or build and return a new object
    return node;
}
```

The function **must return the node** — returning `undefined` is treated as "no change to write back". The returned object replaces the node’s payload for the new version.

## Where editors are used

Editors appear in both `lib-node` and `lib-content`. The two cover different repositories and should not be mixed.

> **Warning:** **Never use `lib-node` to manipulate content.** The CMS repository is layered on top of `lib-node` with content-type validation, draft/master synchronization, publish-state bookkeeping, audit-log entries, child-project propagation, and indexing of system fields. Direct `lib-node` writes against a content node bypass all of that and corrupt the content model.

Reach for `lib-content` whenever the target is content. Use `lib-node` only for custom (non-content) repositories.

| Function | Receives | Notes |
| --- | --- | --- |
| [`lib-node.update`](docs/code/stable/libraries/lib-node.md#update) | Full node | General-purpose write. Re-indexes the node. |
| [`lib-node.patch`](docs/code/stable/libraries/lib-node.md#patch) | Full node | Low-level. Optionally targets multiple branches; can backport a single change. |

| Function | Receives | Notes |
| --- | --- | --- |
| [`lib-content.update`](docs/code/stable/libraries/lib-content.md#update) | Full content (incl. `data`, `publish`, `workflow`) | Validates against the content type unless `requireValid: false`. |
| [`lib-content.patch`](docs/code/stable/libraries/lib-content.md#patch) | Partial content shape | The canonical tool for content upgrades and data migrations. Skips validation and accepts a `branches` list. Callback parameter is named `patcher` but follows the same editor pattern. |
| [`lib-content.updateMetadata`](docs/code/stable/libraries/lib-content.md#updatemetadata) | `{ source, owner, variantOf }` | Scoped editor for content metadata only. |
| [`lib-content.updateWorkflow`](docs/code/stable/libraries/lib-content.md#updateworkflow) | `{ source, state }` | Scoped editor for the workflow state. |

> **Note:** Earlier XP releases exposed `modify` (in both `lib-node` and `lib-content`) for the same role as `update`. `modify` is deprecated — use `update`. The two coexist for backward compatibility, but new code should use `update` to stay consistent with the rest of the API surface.

## Examples

### Update a content field

The most direct use: receive the content, change what you need, return it.

```typescript
import { update } from '/lib/xp/content';

const updated = update({
    key: '/site/articles/launch',
    editor: (content) => {
        content.displayName = 'Launch announcement';
        content.data.summary = 'We shipped today.';
        content.workflow.state = 'READY';
        return content;
    },
});
```

### Append to a list without losing concurrent writes

Because the engine applies the editor to the **current** node version, list appends are safe under concurrent writers — the editor sees whichever version is most recent at the moment it runs.

The example below targets a **custom** (non-content) repository, which is the only place `lib-node` should be used directly.

```typescript
import { connect } from '/lib/xp/node';

const repo = connect({ repoId: 'my.app:custom', branch: 'master' });

repo.update({
    key: nodeId,
    editor: (node) => {
        node.tags = [...(node.tags ?? []), 'reviewed'];
        return node;
    },
});
```

A naive read-then-write in application code would race; the editor pattern does not.

### Migrate content with `patch`

`lib-content.patch` is the workhorse for content upgrades and data migrations. Unlike `update`, it skips content-type validation — exactly what you want when the schema has changed and existing contents do not yet match the new shape.

Pair it with a query (see [Query DSL](docs/code/stable/storage/querying.md)) to walk the affected contents and apply the change to each:

```typescript
import { query, patch } from '/lib/xp/content';

const hits = query({
    query: {
        boolean: {
            must: [{ term: { field: 'type', value: 'com.example:article' } }],
            mustNot: [{ exists: { field: 'data.reviewedAt' } }],
        },
    },
    count: -1,
}).hits;

hits.forEach(({ _id }) => {
    patch({
        key: _id,
        patcher: (content) => {
            content.data = {
                ...content.data,
                reviewedAt: new Date().toISOString(),
            };
            return content;
        },
    });
});
```

### Apply the same change across branches

`patch` accepts a `branches` list. If a branch already has the new version from another branch in the list, it’s switched to point at that version instead of being patched again — useful for backporting a fix from draft to master without forking the version history.

```typescript
import { patch } from '/lib/xp/content';

patch({
    key: '/site/articles/launch',
    branches: ['draft', 'master'],
    patcher: (content) => {
        content.data = {
            ...content.data,
            byline: 'Editorial team',
        };
        return content;
    },
});
```

### Transition workflow state without touching data

`updateWorkflow` gives you an editor that only sees the workflow envelope, so you can’t accidentally write to `data`. Use it when the only intent is to move a content through review.

```typescript
import { updateWorkflow } from '/lib/xp/content';

updateWorkflow({
    key: '/site/articles/launch',
    editor: (w) => {
        w.state = 'READY';
        return w;
    },
});
```

`updateMetadata` follows the same shape for owner and variant changes.

## Notes

- **No-op edits still produce a new version.** If you want to skip the write when nothing changed, gate the editor call upstream — the editor itself can’t suppress the version bump once it runs.

- **`update` validates; `patch` doesn’t.** Use `update` for routine content changes. Reach for `patch` when migrating content to a new schema, backporting a change across branches, or otherwise intentionally bypassing content-type validation.

- **Editors run as the calling principal.** For changes that exceed the caller’s permissions — bulk fixes, migrations — wrap the editor block in [`lib-context.run`](docs/code/stable/libraries/lib-context.md#run) with a service principal. See [Permissions](docs/code/stable/storage/permissions.md#_running_as_a_different_principal) for the pattern.
