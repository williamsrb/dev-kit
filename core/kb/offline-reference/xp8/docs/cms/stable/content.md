<!-- src:https://developer.enonic.com/docs/cms/stable/content generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content.md

# Content

Content is the core entity in Enonic CMS. Every content item has a specific content type and life cycle.

## Introduction

Content is normally managed via Content Studio, but can also be accessed and manipulated programmatically via APIs. Content items have a specific [Content Type](docs/cms/stable/content/content-types.md), which defines its data structure and capabilities. Content items are stored in isolated [Content Projects](docs/cms/stable/projects.md), and can optionally be organized as a [hierarchy](docs/cms/stable/content/hierarchy.md) within each project.

## Standard properties

Content items are stored in JSON format, within an XP repo. Every content item has a set of standard properties that are automatically generated and maintained via the Content API. Below is an overview of the JSON structure of a content item:

```JSON
{
  "_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  (1)
  "_name": "my-article",  (2)
  "_path": "/my-site/articles/my-article",  (3)
  "_parentPath": "/my-site/articles",
  "_versionKey": "f1e2d3c4-b5a6-7890-abcd-ef1234567890",  (4)
  "_timestamp": "2025-06-15T12:00:00Z",  (5)
  "_sortorder": "modifiedTime DESC",  (6)
  "_manualordervalue": 0,

  "type": "com.example:article",  (7)
  "language": "en",  (8)

  "displayName": "My Article",  (9)
  "data": { ... }, (10)
  "x": [ ... ],  (11)
  "components": [ ... ],  (12)
  "attachments": [ ... ],  (13)

  "creator": "user:system:admin",  (14)
  "createdTime": "2025-01-01T10:00:00Z",
  "modifier": "user:system:editor",
  "modifiedTime": "2025-06-15T12:00:00Z",
  "owner": "user:system:admin",

  "publish": {  (15)
    "from": "2025-01-15T08:00:00Z",
    "to": "2026-01-15T08:00:00Z",
    "first": "2025-01-15T08:00:00Z",
    "time": "2025-06-15T12:00:00Z"
  },

  "_references": [ ... ],  (16)
  "_alltext": "My Article ...",  (17)
  "_score": 1.23,  (18)
  "_permissions": { ... }  (19)

}
```

| ****1** | **_id** — unique content identifier (UUID), generated automatically. |
| --- | --- |
| ****2** | **_name** — content name, used in the URL path. |
| ****3** | **_path** / **_parentPath** — full content path, and parent path. |
| ****4** | **_versionKey** — identifier of the current content version. |
| ****5** | **_timestamp** — last change to the content version. |
| ****6** | **_sortorder** / **_manualordervalue** — controls default sorting of child items. Defaults to `modifiedTime DESC`. |
| ****7** | **type** — the qualified content type name. Set at creation, cannot be changed. |
| ****8** | **language** — locale of the content. |
| ****9** | **displayName** — human-readable name, typically used in lists, search results, and as the content title. |
| ****10** | **data** — the editorial content, structured according to the [content type](docs/cms/stable/content/content-types.md) form definition. |
| ****11** | **x** — structured by [mixin](docs/cms/stable/content/mixins.md) form definition, grouped by namespaced keys. |
| ****12** | **components** — present if the item contains a [page](docs/cms/stable/pages.md) with components. |
| ****13** | **attachments** — optional array of [attachments](docs/cms/stable/content/attachments.md) stored within the content item. |
| ****14** | **creator** / **createdTime** / **modifier** / **modifiedTime** / **owner** — audit trail properties. |
| ****15** | **publish** — publishing metadata. `from`/`to` define the publish window. `first` is set on first publish and never changes. `time` is updated on every publish. |
| ****16** | **_references** — aggregation of all outbound [references](docs/cms/stable/content/references.md) to other content items in the project. |
| ****17** | **_alltext** — all fulltext-analyzed fields (TextLine, TextArea, HtmlArea) gathered in one property, used for search. |
| ****18** | **_score** — calculated relevance score, only present in search results. |
| ****19** | **_permissions** — [access control](docs/cms/stable/content/permissions.md) settings for the content item. |
