<!-- src:https://developer.enonic.com/docs/cms/stable/content/versions generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content/versions.md

# Versions

Every content item keeps a complete, immutable version history. Each edit produces a new, read-only snapshot of the item, so you can reconstruct exactly what the content looked like at any point in time, see who changed it, and roll back to an earlier state. Versions are created automatically — there is nothing to configure.

## How versions are created

A new version is committed whenever the stored state of an item changes. The most common triggers are:

| Action | Effect |
| --- | --- |
| **Create** | The initial version of a newly created item. |
| **Edit** | Any change to the item’s data, metadata, or form values. |
| **Move / rename** | Changing the item’s `_path` or `_name`. |
| **Sort** | Changing the manual ordering of child items. |
| **Publish** | Copies the current draft version onto the `master` branch (see below). |
| **Unpublish** | Removes the item from `master`; the draft version is retained. |
| **Mark as ready** | Promoting the workflow state to `READY` (see [Content lifecycle](docs/cms/stable/content/lifecycle.md)). |

Each version records the audit metadata of the change — the timestamp and the user responsible — so the history doubles as an audit trail.

## Versions and branches

Content lives on two branches: `draft` (the editor’s working copy) and `master` (the published copy the public sees). Both branches are simply pointers into the same version history:

- Editing an item adds a version and moves the `draft` pointer to it.

- Publishing **commits** the current `draft` version and moves the `master` pointer to that same version.

Because both branches reference the version history, the published item on `master` and the work-in-progress on `draft` may point to different versions of the same content. This divergence is what the change state (`MODIFIED`, `MOVED`, and so on) describes in [Content lifecycle](docs/cms/stable/content/lifecycle.md#change-state).

The current version of an item on a given branch is identified by its `_versionKey`, one of the [standard content properties](docs/cms/stable/content.md#standard-properties):

```JSON
{
  "_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "_versionKey": "f1e2d3c4-b5a6-7890-abcd-ef1234567890", (1)
  "_timestamp": "2026-06-15T12:00:00Z", (2)
  "modifier": "user:system:editor",
  "modifiedTime": "2026-06-15T12:00:00Z"
}
```

| ****1** | **_versionKey** — identifier of the version this branch currently points to. Comparing the `_versionKey` of an item on `draft` versus `master` tells you whether the published copy is behind the draft. |
| --- | --- |
| ****2** | **_timestamp** — the time this particular version was committed. |

> **Note:** In a [layered project](docs/cms/stable/content/layering.md#versions), only versions created within a given layer are visible in that layer. Versions are not "polluted" by changes inherited from surrounding layers.

## Comparing and restoring

In Content Studio, the **Version history** panel lists every version of the selected item as a timeline of events (created, edited, published, unpublished, sorted, marked as ready), each stamped with the time and the responsible user. From there an editor can:

- **Compare** any two versions to see a field-by-field diff of what changed.

- **Revert** to an earlier version, which copies that snapshot into a new `draft` version. Reverting never deletes history — it simply adds a new version on top.

## Accessing versions

For headless consumers, the relevant choice is almost always **which branch** to read, not which historical version. Selecting a branch resolves to that branch’s current version:

- Query `master` (the default) for the published content the public should see.

- Query `draft` for unpublished, in-progress content — for example, to drive a preview.

```graphql
{
  guillotine(branch: "draft") { (1)
    get(key: "/site/articles/hello") {
      _id
      displayName
      modifiedTime
    }
  }
}
```

| ****1** | Without `branch`, Guillotine reads `master`. See the [Guillotine documentation](https://developer.enonic.com/docs/guillotine) for branch selection. |
| --- | --- |

Reading arbitrary points in the version history — listing all versions of an item — is not exposed in the headless query API by default. You may access this functionality through the Content API, and optionally expose it through a [Guillotine extension](docs/cms/stable/apis/graphql.md#extending-the-schema) or a custom API. Visit the [Enonic Development Kit](https://developer.enonic.com/docs/code) documentation for details.
