<!-- src:https://developer.enonic.com/docs/cms/stable/content/lifecycle generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content/lifecycle.md

# Content lifecycle

Every content item carries three independent state dimensions — what the public sees, how the draft compares to the published version, and where the item sits in the editorial workflow. Content Studio surfaces each dimension in a different UI surface so everyday use stays uncluttered.

> **Note:** The publish and change states were split into two separate indicators in XP {release} / Content Studio 6. Earlier versions combined them into a single status.

## Publish state

The publish state describes whether the item is visible to public consumers — readers of the `master` branch. It is derived from the publish window and the archive flag, not set directly by editors.

| State | Meaning |
| --- | --- |
| `OFFLINE` | Never published, or explicitly unpublished. Not present on the `master` branch. |
| `SCHEDULED` | Published with `publish.from` in the future. Present on `master` but not yet visible to the public. |
| `ONLINE` | Currently published and within the publish window — visible to the public. |
| `EXPIRED` | Was published, but `publish.to` is in the past. Still on `master`, no longer visible to the public. |
| `ARCHIVED` | Moved to the archive. Not returned by standard queries but preserved for restoration. |

The publish state is what appears in Content Studio list views — the indicator the editor sees at a glance.

## Change state

The change state describes how the current draft compares to the published version. It is surfaced during edit and publish dialogs, where the editor needs to understand what will actually change on publish.

| State | Meaning |
| --- | --- |
| `NEW` | Exists only in draft. There is no published version yet. |
| `MODIFIED` | Published, with uncommitted draft edits. Publishing will update the `master` copy. |
| `MOVED` | Published, but the draft has since been moved to a different path. Publishing will update the path on `master`. |
| `UNPUBLISHED` | Was published, has since been unpublished. The draft remains and can be published again. |

## Workflow state

The workflow state is a separate, editor-controlled dimension that indicates whether the draft is considered complete.

| State | Meaning |
| --- | --- |
| `IN_PROGRESS` | The draft is being worked on. |
| `READY` | The draft is considered complete and ready for publishing. |

A content item can only be promoted from `IN_PROGRESS` to `READY` when all checks pass. One check currently runs:

- **Validity** — all required fields have values, and every value satisfies the form’s validation rules (types, occurrences, regex patterns, and so on).

If the validity check fails, Content Studio highlights the fields that need attention and the promotion is blocked.

## Querying via GraphQL

The publish window and audit timestamps are exposed directly on every content item:

```graphql
{
  guillotine {
    get(key: "/site/articles/hello") {
      _id
      displayName
      createdTime
      modifiedTime
      publish {
        first
        time
        from
        to
      }
    }
  }
}
```

Response

```JSON
{
  "data": {
    "guillotine": {
      "get": {
        "_id": "f3076b5c-ea45-4c8b-8c06-1f87b8d8cdd9",
        "displayName": "Hello world",
        "createdTime": "2026-01-10T10:00:00Z",
        "modifiedTime": "2026-01-15T08:00:00Z",
        "publish": {
          "first": "2026-01-12T09:00:00Z", (1)
          "time": "2026-01-15T08:00:00Z", (2)
          "from": "2026-01-15T08:00:00Z", (3)
          "to": null (4)
        }
      }
    }
  }
}
```

| ****1** | **first** — the first time this content was ever accessible online. Set on the initial publish and never updated, even if the item is later unpublished and republished. |
| --- | --- |
| ****2** | **time** — the time the editor pressed publish for the specific version. Updated on every publish. If the current item in draft branch has never been published, this field is `null`. |
| ****3** | **from** — start of the current publish window. The content is present on `master` and becomes visible to the public at this time. |
| ****4** | **to** — end of the current publish window. Content remains on master, but is no longer visible to the public. `null` means no expiry date. |

Find every item scheduled to go online in the future:

```graphql
{
  guillotine {
    queryDsl(
      query: {
        range: {
          field: "publish.from",
          gte: { string: "now" }
        }
      },
      sort: { field: "publish.from", direction: DESC }
    ) {
      _id
      displayName
      publish { from }
    }
  }
}
```

Response

```JSON
{
  "data": {
    "guillotine": {
      "queryDsl": [
        {
          "_id": "a1111111-1111-4111-8111-111111111111",
          "displayName": "Upcoming announcement",
          "publish": {
            "from": "2026-06-01T08:00:00.000Z"
          }
        },
        {
          "_id": "b2222222-2222-4222-8222-222222222222",
          "displayName": "Spring campaign launch",
          "publish": {
            "from": "2026-05-25T09:30:00.000Z"
          }
        }
      ]
    }
  }
}
```

Find every draft whose current version is not live on `master` — items that need (re)publishing. `publish.time` is set when the current draft version has been published; an unset value covers both never-published content (`NEW`) and items that have been edited, moved, or unpublished since their last publish (`MODIFIED`, `MOVED`, `UNPUBLISHED`).

To restrict the query to content that has never been published at all, filter on `publish.first` instead — that field is only set on the very first publish and never cleared.

```graphql
{
  guillotine(branch: "draft") {
    queryDsl(
      query: {
        boolean: {
          mustNot: [
            { exists: { field: "publish.time" } }
          ]
        }
      },
      sort: { field: "modifiedTime", direction: DESC }
    ) {
      _id
      displayName
      modifiedTime
      publish { time }
    }
  }
}
```

Response

```JSON
{
  "data": {
    "guillotine": {
      "queryDsl": [
        {
          "_id": "c3333333-3333-4333-8333-333333333333",
          "displayName": "Q2 roadmap update",
          "modifiedTime": "2026-05-18T12:14:02.000Z",
          "publish": { "time": null }
        },
        {
          "_id": "d4444444-4444-4444-8444-444444444444",
          "displayName": "Onboarding revamp",
          "modifiedTime": "2026-05-17T09:40:11.000Z",
          "publish": { "time": null }
        }
      ]
    }
  }
}
```

> **Note:** Guillotine queries the `master` branch by default, so the query above sets `branch: "draft"`. The query resolves `NEW`, `MODIFIED`, `MOVED`, and `UNPUBLISHED` change states. See the [Guillotine documentation](https://developer.enonic.com/docs/guillotine) for branch selection details.

## Audit trail

Every content item preserves enough history to reconstruct what changed, when, and by whom — see [Versions](docs/cms/stable/content/versions.md) for how to access prior states and compare them.

Full audit properties (`creator`, `createdTime`, `modifier`, `modifiedTime`, `owner`, `_timestamp`) are documented under [standard content properties](docs/cms/stable/content.md#standard-properties).
