<!-- src:https://developer.enonic.com/docs/code/stable/storage/permissions generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/storage/permissions.md

# Permissions

API patterns for managing and querying node permissions from application code.

> **Note:** This chapter assumes the conceptual model — permission types, principal resolution, and how permissions behave across branches — is already familiar. If not, see the [XP storage documentation](docs/platform/stable/storage.md) for the platform-level concepts.

## Reading the ACL

`lib-node` exposes a function to read the ACL on a single node, returning the list of access-control entries that target that node.

Use this when you need to inspect or audit who has access to a given node, or as the starting point for an incremental update (read, modify, write back).

## Writing the ACL

`lib-node` writes permissions in two forms:

Set

Replace the ACL on a single node.

Apply

Replace the ACL on a target node and, optionally, on all of its descendants.

Both operations update the affected nodes across every branch where they exist — there is no per-branch ACL state, and no separate step to publish permission changes between branches.

When applying hierarchically, the descendant set is computed from the node tree in the branch the call runs in (selected via `lib-context`). Once the set is determined, the ACL change is written to each of those nodes everywhere they appear.

Setting an ACL replaces it entirely — there is no "add one entry" operation. To grow an ACL incrementally, read the current ACL, modify it in memory, and write the result back.

New nodes are created with a copy of the parent’s ACL as their initial state. This is a one-shot copy: later changes to the parent’s ACL do not propagate to existing children. To explicitly seed a different ACL at create time, pass it as part of the create call.

## Repository root permissions

Every repository has a root node with the fixed ID `000-000-000-000`. Its ACL governs operations performed against the repository root, but does not act as a default for descendants — every node has its own explicit ACL.

`lib-repo` exposes functions to read and write root permissions when creating or reconfiguring a repository.

> **Tip:** When programmatically creating a repository, set root permissions explicitly and seed initial ACLs on the content you populate. There is no parent-inheritance fallback if you forget.

## Querying by permission

The effective ACL on each node is flattened into indexed system properties at write time. Each property is named `*permissions*` and lists the principal keys that hold that permission:

| Indexed property | Lists principals with |
| --- | --- |
| `_permissions_read` | `READ` |
| `_permissions_create` | `CREATE` |
| `_permissions_modify` | `MODIFY` |
| `_permissions_delete` | `DELETE` |
| `_permissions_publish` | `PUBLISH` |
| `_permissions_readpermissions` | `READ_PERMISSIONS` |
| `_permissions_writepermissions` | `WRITE_PERMISSIONS` |

These can be used in any [query](docs/code/stable/storage/querying.md) — for example, to find every node a given role can modify:

```json
{
  "query": {
    "term": {
      "field": "_permissions_modify",
      "value": "role:my.editors"
    }
  }
}
```

> **Note:** XP already filters query results by the caller’s `READ` permission. The `*permissions**` properties are for queries *about* permissions, not *for* enforcing them.

## Running as a different principal

Node operations execute under the calling user’s permissions by default. To perform work that requires broader access — system maintenance, bulk imports, applying permission changes across a subtree — run the operation inside a `lib-context` block scoped to a service principal (typically `role:system.admin`) and the target repository and branch.

> **Caution:** Code running in an elevated context bypasses node-level access checks entirely. Keep elevated blocks as narrow as possible, and never pass unsanitised user input into one.

## Auditing

Permission changes on content nodes appear in the audit log as `system.content.applyPermissions` events. For nodes outside the CMS repository, log changes from your application if you need an audit trail.
