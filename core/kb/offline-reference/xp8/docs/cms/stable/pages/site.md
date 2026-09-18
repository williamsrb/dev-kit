<!-- src:https://developer.enonic.com/docs/cms/stable/pages/site generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/pages/site.md

# Sites

A site is the root (front-page) of a website within a content project. It is a built-in content type (`portal:site`) that binds applications to a content sub-tree and unlocks the page-building features.

## Introduction

Creating a site turns an ordinary branch of the content tree into a website. It does three things:

- **Binds applications** to a scope — the schemas, components and extensions of the selected apps become available to content beneath the site.

- **Unlocks the page concept** — once a site exists, the content within it can manage [pages](docs/cms/stable/pages/page.md), [page templates](docs/cms/stable/pages/page-templates.md) and [fragments](docs/cms/stable/pages/fragments.md).

- **Defines a URL root** — the site is the root of the URL structure for the website it represents.

A site is a regular content item, so it is versioned, permissioned and published like any other content. Sites can be created anywhere in the hierarchy, but are commonly placed at the project root.

## Site applications

Adding an application to a site makes that app’s content types, components, mixins and other schemas available within the site’s scope — the same mechanism used at the [project](docs/cms/stable/projects.md#applications) level, but here it is scoped to a single site rather than the whole repository.

This is also how purpose-specific apps (a `sitemap.xml` generator, SEO metafields, redirects, and similar) introduce site-relative features.

> **Note:** Apps may also contribute to Enonic’s built-in rendering as documented in the [Enonic Development Kit](https://developer.enonic.com/docs/code) docs.

## Site configuration

When an app is added to a site, the configuration form declared in its [CMS descriptor](docs/cms/stable/schemas/cms-descriptor.md) is shown to the administrator. The submitted values are persisted on the site content alongside the application binding and are available to the app at runtime. This is the same mechanism as [project configuration](docs/cms/stable/projects.md#applications) — site config applies to a single site, project config to the whole repository — and changes take effect immediately, without redeploying the app.

> **Important:** Configuration values are **not** exposed through the [GraphQL API](docs/cms/stable/apis/graphql.md) by default. Because config commonly holds secrets — API keys, tokens, endpoint credentials — it is kept server-side and is not queryable as content data.

If a front-end genuinely needs a configuration value, the app must **deliberately expose** the selected fields, for example through a [Guillotine extension](docs/cms/stable/apis/graphql.md#extending-the-schema). Nothing in `siteConfig` becomes queryable automatically.

## Definition (portal:site)

The Site content type has the following definition:

super-type

base:structured

is-abstract

false

is-final

true

allow-child-content

true

## Output

The stored value of a site carries a `siteConfig` array — one entry per bound application, each pairing the `applicationKey` with the values captured by that app’s configuration form:

```JSON
{
  "_id": "d4e5f6a7-...",
  "_name": "my-site",
  "_path": "/my-site",
  "type": "portal:site",
  "displayName": "My Site",
  "data": {
    "siteConfig": [
      {
        "applicationKey": "com.example.blog",
        "config": {
          "apiKey": "••••••••",
          "postsPerPage": 10
        }
      }
    ]
  }
}
```

When a single application is bound, `siteConfig` is a single object rather than an array.

## GraphQL

A site is a content item, so it is queried like any other content — by path or id — and exposes the standard content fields:

```graphql
{
  guillotine {
    get(key: "/my-site") {
      _id
      _path
      displayName
      type
    }
  }
}
```

The `config` values inside `siteConfig` are **not** available in the GraphQL API by default, for the security reasons described under [Site configuration](#_site_configuration). To read a configuration value from a headless front-end, the owning application must expose it explicitly through a [Guillotine extension](docs/cms/stable/apis/graphql.md#extending-the-schema).
