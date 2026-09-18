<!-- src:https://developer.enonic.com/docs/cms/stable/integrations generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/integrations.md

# Integrations

The CMS is designed to be embedded in a larger ecosystem. Front-end clients read content over the built-in [Web APIs](docs/cms/stable/apis.md), while integrations with external systems — analytics, search, CRM, PIM, AI services, import pipelines — plug into the CMS through extension points exposed by the XP platform.

> **Note:** The built-in Web APIs (GraphQL, Image, Attachment) are **read-only**. Programmatic writes — creating or updating content from external systems — are done by exposing your own endpoints through [custom functions](#extending-the-cms) that internally use the server-side JavaScript APIs.

## Extending the CMS

Custom integration logic lives in Enonic apps, which are deployed alongside the CMS and have full access to the platform. An app can:

- **Expose custom HTTP endpoints** under `/api/.` for inbound writes, RPC, webhooks, or any protocol the built-in APIs don’t cover.

- **Extend the GraphQL schema** — register a [Guillotine extension](docs/cms/stable/apis/graphql.md#extending-the-schema) that adds custom queries, mutations, types, and resolvers alongside Guillotine’s generated types.

- **Listen to content events** — publish, modify, delete — and react by syncing to external systems, invalidating caches, or kicking off workflows.

- **Run scheduled or on-demand tasks** for periodic imports, exports, batch processing, or housekeeping.

- **Access the server-side Content API** (`lib-content`, `lib-scheduler`, etc.) to read and write content, manage versions, and traverse the repository from within these functions.

- Integrate with external systems, perform complex data processing, or implement custom business logic as needed.

- Access the low level NoSQL storage via the Node API for storing non-editoral data.

These capabilities are part of the standard Enonic XP app surface. See the [Enonic Development Kit](https://developer.enonic.com/docs/code) for scaffolding, build, and deployment details.

## Extending Content Studio

Beyond programmatic integration, Content Studio is itself extensible through Enonic apps:

- **Custom selectors** — pull options from external data sources (catalogs, taxonomies, third-party services) into a field; see [CustomSelector](docs/cms/stable/schemas/form-items/customselector.md).

- **Widgets and panels** — add bespoke tools, dashboards, or previews to the Studio chrome.

- **Custom validators** — enforce business rules, integrate approval systems, or trigger external review processes.

See the [Enonic Development Kit](docs/code/stable/web/extensions.md) for examples of extending Content Studio.

## Ready-made apps

Enonic and the community publish ready-to-run integration apps on [Enonic Market](https://market.enonic.com), covering common needs — analytics (Google Analytics, Matomo), SEO tooling, sitemap and feed generation, AI services, and more. Apps install into your XP environment alongside the CMS and typically expose configuration through Content Studio.

When an off-the-shelf app meets the need, prefer it over building from scratch. When it doesn’t, build a custom one — or fork an existing app as a starting point.
