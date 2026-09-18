<!-- src:https://developer.enonic.com/docs/cms/stable/content/permissions generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content/permissions.md

# Permissions

Every content item carries an access-control list (ACL) that determines which principals may read, modify, publish, and otherwise act on it.

## Permission types

A content item grants seven independent permissions, each enabling a specific operation:

READ

Retrieve the content item and its properties. Without READ, the item is invisible to the caller — queries skip it, direct fetches return "not found".

CREATE

Create child content directly under this item.

MODIFY

Edit the item’s data, displayName, or any property other than its ACL.

DELETE

Remove the item from the project.

PUBLISH

Push the item from `draft` to `master` (or unpublish in the reverse direction).

READ_PERMISSIONS

Read the ACL of this item.

WRITE_PERMISSIONS

Change the ACL of this item.

The seven permissions are independent — granting `MODIFY` does not imply `READ`, though in practice ACLs are written to grant logical bundles.

## Principals

Permissions are granted to **principals** — actors known to the IAM system. Three principal types are recognised in ACL entries:

user:<idprovider>:<username>

A specific user, e.g. `user:default:alice`.

group:<idprovider>:<groupname>

A group of users; granting to a group grants to every member.

role:<rolename>

A role; granting to a role grants to every user holding it, directly or transitively.

Matching is transitive — when XP evaluates whether a caller may act on a content item, it walks every group the caller belongs to and every role they hold (including via group membership) and unions the granted permissions.

### Built-in roles relevant to CMS

role:system.everyone

Any caller, including unauthenticated/anonymous requests. Granting `READ` to this role makes a content item publicly readable.

role:system.authenticated

Any signed-in caller.

role:system.admin

Platform-level superuser; bypasses content ACLs.

role:cms.admin

CMS-wide admin; full access across all projects.

role:cms.expert

CMS developer-level access.

role:cms.user

Baseline role for any user of Content Studio.

Each [project](docs/cms/stable/projects.md#roles) also defines its own roles (Owner / Editor / Author / Contributor / Viewer), registered under principal IDs of the form `role:com.enonic.cms.project..`.

## ACL model

The ACL is **allow-only** — each entry lists permissions granted to one principal; there are no deny entries. Effective permission for a caller is the union of every entry whose principal matches.

The ACL appears on a content item as the `_permissions` property:

```JSON
{
  "_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "_path": "/my-site/articles/my-article",
  "_permissions": [
    {
      "principal": "role:system.everyone",
      "allow": ["READ"]
    },
    {
      "principal": "role:com.enonic.cms.project.myproject.author",
      "allow": ["READ", "CREATE", "MODIFY", "DELETE"]
    },
    {
      "principal": "role:com.enonic.cms.project.myproject.owner",
      "allow": ["READ", "CREATE", "MODIFY", "DELETE", "PUBLISH", "READ_PERMISSIONS", "WRITE_PERMISSIONS"]
    }
  ]
}
```

## Inheritance: copy-on-create

When a content item is created, it receives a **copy** of its parent’s ACL as its initial state. From that point on the two ACLs are independent — **changes to the parent’s ACL do not propagate**.

> **Important:** There is no live inheritance and no `inheritPermissions` flag. The flag from earlier XP versions was removed in XP 8 in favour of explicit recursive updates. To roll an ACL change down a subtree, use the **apply** operation described below.

### Applying an ACL change to descendants

To update an ACL across an existing subtree, callers explicitly invoke the recursive **apply** operation. This walks every descendant under a given path and replaces (or merges) their ACLs in one administrative pass. Editors trigger this via Content Studio’s permission dialog ("Apply to children"); programmatic callers use the corresponding `lib-content` function.

See the [permissions reference in the Enonic Development Kit](docs/code/stable/storage/permissions.md) for the function signatures and merge semantics.

## Query semantics

Every query is **implicitly filtered** by the caller’s `READ` permission. Items the caller cannot read are removed before hits, total counts, and aggregation buckets are returned. The same query run anonymously, as an editor, or as a system admin produces different result sets — see [Content Querying](docs/cms/stable/querying.md) for the broader implication.

XP also indexes each ACL into per-permission system fields so you can query **about** permissions:

`_permissions_read`, `_permissions_create`, `_permissions_modify`, `_permissions_delete`, `_permissions_publish`, `_permissions_readpermissions`, `_permissions_writepermissions`

Each field contains the list of principals that ultimately hold the corresponding permission on the item. Example: find every item modifiable by a given project’s editor role:

```JSON
{
  "term": {
    "field": "_permissions_modify",
    "value": { "string": "role:com.enonic.cms.project.myproject.editor" }
  }
}
```

The indexed fields support permission-aware queries; they do not bypass the implicit read filter — the caller still only sees items they themselves have `READ` on.

## Querying via GraphQL

Guillotine exposes the ACL on the `Content` interface via the `_permissions` field. Useful for editorial UIs that need to render who-can-do-what without re-fetching from a separate endpoint.

```graphql
{
  guillotine {
    get(key: "/my-site/articles/my-article") {
      _id
      displayName
      _permissions {
        principal {
          key
          displayName
        }
        allow
      }
    }
  }
}
```

> **Note:** The Guillotine schema mirrors the underlying ACL — query the field reference in the [Guillotine documentation](https://developer.enonic.com/docs/guillotine/stable) for the exact field shape, since it evolves with Guillotine versions.

## Where permissions come from

For a freshly-created content item, the initial ACL is the copy of the parent’s ACL — and ultimately the project’s root item, whose ACL is shaped by the [project’s access mode](docs/cms/stable/projects.md#access-mode) and granted [project roles](docs/cms/stable/projects.md#roles). See [Content projects](docs/cms/stable/projects.md) for the project-level model.

For layered projects, each [layer](docs/cms/stable/content/layering.md) carries its own ACLs — see the layering page for inheritance behaviour between parent and child layers.

## See also

- [XP platform docs — permissions model](docs/platform/stable/storage/permissions.md) for the underlying node-level mechanics shared across all XP storage, not just CMS content.

- [Enonic Development Kit — permissions](docs/code/stable/storage/permissions.md) for the `lib-content` / `lib-node` function signatures used to read and modify ACLs programmatically.
