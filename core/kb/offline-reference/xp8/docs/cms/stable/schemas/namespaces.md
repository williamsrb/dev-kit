<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/namespaces generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/namespaces.md

# Namespaces

Namespaces scope schemas to their package and prevent collisions between independent providers.

## Identifier

Every schema is identified as `:` (e.g. `com.example.myapp:article`). The namespace scopes a **schema package** — the unit of schemas shipped together — and prevents collisions between independent providers that happen to use the same schema name.

A namespace is a dot-separated identifier — you pick whatever name fits your package (e.g. `com.example.myapp`, `acme.editorial`, `myschemas`). Reverse-DNS (`com..`) is a common convention but not required.

Each dot-separated segment must start with a letter and may contain letters, digits, and underscores. Lowercase is the convention.

## Reserved namespaces

The following namespaces are **reserved** for built-in schemas:

base

[Structural content types](docs/cms/stable/content/built-in-types.md) (`base:folder`, `base:shortcut`, `base:unstructured`).

portal

[Sites and pages](docs/cms/stable/pages.md) types (`portal:site`, `portal:page-template`, `portal:fragment`, `portal:template-folder`).

media

[Media types](docs/cms/stable/media/media-types.md) (`media:image`, `media:document`, etc.).

## Where the namespace comes from

Currently, the namespace of a schema package is the **application name** of the XP app that ships it. An app named `com.example.myapp` produces schemas in the `com.example.myapp` namespace — the developer does not declare it explicitly.

> **Note:** Support is being introduced for explicit namespace declaration, decoupling a schema package from the host app. This will allow schemas to be authored and managed independently of XP app installation. The `<namespace>:<name>` identifier rules and reserved-namespace list remain the same.

## Encoding in stored content and APIs

The literal `:` identifier is preserved in some contexts and re-encoded in others, depending on what characters are legal in the surrounding format.

**Values preserved**

- For values, such as in the `type` field on a content item — e.g. `"type": "com.example.myapp:article"`. Use this exact form for content queries against `type` (Query DSL, `queryDsl` in Guillotine). See [Content](docs/cms/stable/content.md).

**Re-encoded**

- **Property names** (where namespaces are used in property names): dots become dashes — `com.example` → `com-example`. A `city` field on `com.example:address` is stored at `x.com-example.address.city`. See [Mixins](docs/cms/stable/content/mixins.md) for more examples.

- **Guillotine GraphQL types**: dots and dashes become underscores — `com.example.myapp:news-article` → `com_example_myapp_news_article`. See [Content Types](docs/cms/stable/content/content-types.md) for the full table.
