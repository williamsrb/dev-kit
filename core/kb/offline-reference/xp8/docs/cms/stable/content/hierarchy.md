<!-- src:https://developer.enonic.com/docs/cms/stable/content/hierarchy generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content/hierarchy.md

# Content hierarchy

Content items in a project can be organized as a tree, with parent-child relationships reflected in their paths.

## Model

Every content item within a project lives in a single tree. Each item has exactly one parent — either another content item or the project root — and any number of children. The root of the tree is the project itself.

Using the hierarchy is **optional**. You may store every content item directly under the project root in a flat list if that fits your model, or build a deep tree of folders and child items. Common reasons to use the hierarchy:

- **Internal organization** — group related content (articles by year, products by category, assets by department) for editorial convenience.

- **URL space for sites** — when a [site](docs/cms/stable/pages.md) is part of the tree, the content path doubles as the site’s URL path, so the editorial structure directly shapes how pages are addressed on the public web.

## Path mechanics

Each item has a slash-separated `_path` representing its ancestry, and a `_name` that forms the trailing segment:

```JSON
{
  "_name": "my-article",
  "_path": "/my-site/articles/my-article",
  "_parentPath": "/my-site/articles"
}
```

`_name` must be unique among siblings — two items with the same parent cannot share a name. The constraint is strict and enforced at create-time and on move/rename.

`_id` is a UUID assigned at creation and **never changes**, even when an item is renamed or moved. Move or rename operations recalculate `_path` for the item **and every descendant**; the IDs stay stable, so references between items survive restructuring.

## Type-driven constraints

Whether an item can have children — and which content types are allowed under it — is controlled by the parent’s content type via the `allowChildContent` and `allowChildContentType` settings. See [Content Types](docs/cms/stable/content/content-types.md) for the full rules.

## Querying the tree

Hierarchy-aware queries use the standard `_path` and `_parentPath` fields:

- `_parentPath` term query → direct children of a given parent.

- `pathMatch` query → all descendants under a path prefix. See [Content Querying](docs/cms/stable/querying.md).

- Guillotine exposes typed `parent`, `children`, and `parents` traversal fields on the `Content` interface — see [GraphQL API](docs/cms/stable/apis/graphql.md).
