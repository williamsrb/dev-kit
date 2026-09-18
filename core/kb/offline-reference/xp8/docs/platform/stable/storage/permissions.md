<!-- src:https://developer.enonic.com/docs/platform/stable/storage/permissions generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/storage/permissions.md

# Permissions

XP enforces access control on every [node](docs/platform/stable/storage/repositories.md#nodes) in the data store, all the way down to individual documents.

## Model

Each node carries an Access Control List (ACL). Each entry in the ACL targets a single [principal](docs/platform/stable/security/principals.md) — a user, group, or role — and lists the permissions granted to that principal.

### Permission types

A node defines seven independent permissions:

| Permission | Grants |
| --- | --- |
| `READ` | Retrieve the node and its properties. |
| `CREATE` | Create children directly under this node. |
| `MODIFY` | Edit the node’s properties. |
| `DELETE` | Remove the node. |
| `PUSH` | Push the node from one branch to another (e.g. `draft` → `master` in the CMS). |

### Resolution

When XP evaluates whether a caller may perform an operation, it collects every ACL entry whose principal matches the caller — directly, transitively through group membership, through any role they hold, and through the dynamic [system roles](docs/platform/stable/security/principals.md#system-roles) (`system.everyone` for anyone, `system.authenticated` for signed-in users).

An operation is permitted if at least one matching entry grants it.

### Per-node ACL

Every node carries its own explicit ACL. There is no read-time inheritance from the parent — a change to a parent’s ACL does not automatically flow down to its descendants.

When a node is created, it receives a copy of its parent’s ACL as its starting state. This is a one-time copy, not a live link: subsequent changes to the parent do not affect the new node.

To set the same ACL on many nodes at once, use the hierarchical *apply* operation: the ACL is written to a target node and, optionally, to all its descendants.

The root node of every repository (`000-000-000-000`) carries its own ACL that governs operations performed against the repository root. It does not act as a default for descendants.

### Permissions across branches

A node’s ACL is shared across every [branch](docs/platform/stable/storage/repositories.md#branches) the node exists in. Setting or applying permissions on a node takes effect immediately on that node in every branch — there is no per-branch ACL state and no "publish permissions" step between branches.

When permissions are applied hierarchically, the set of affected descendants is determined by the node tree in the branch where the operation runs. The resulting ACL change is then written to each of those nodes across every branch they appear in.

## Querying

When a node is indexed, its effective ACL is flattened into a set of system properties — one per permission level — listing the principals that ultimately hold that permission. This lets queries filter on permissions efficiently without resolving the full ACL at query time. See the [developer documentation](docs/code/stable/storage/properties.md) for the field reference.

XP also applies an implicit read filter to every query. Callers never see nodes they do not have `READ` access to, regardless of how the query is written.

## Managing permissions

- In the CMS, content permissions are managed through [Content Studio](https://developer.enonic.com/docs/content-studio/stable/workbench/permissions).

- From application code, see the storage permissions reference in the developer documentation.

- Permission changes on content are recorded in the [audit log](docs/platform/stable/security/audit-logs.md) as `system.content.applyPermissions` events.
