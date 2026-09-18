<!-- src:https://developer.enonic.com/docs/react4xp/6.x/release generated:2026-07-30T04:18:15Z format:llm-dense react4xp-6.x -->
#DOC docs/react4xp/6.x/release.md

# React4XP 6 Release notes

New features and improvements since version 5

## Detached front-end

Previous versions were using XP’s site engine directly, meaning that rendering was built and shipped together with the CMS schemas.

V6 severs the tie beween CMS schema definitions and the rendering. This means you may implement the front-end (R4XP) code separately from the CMS schema definition(s). As such, you may deploy front-end and back-end/model as two (or more) separate applications.

## Updated build system

React4XP is now fully aligned with the [TypeScript Starter](https://market.enonic.com/starters/typescript-starter). This means full support for "enonic dev" mode and continuous compilation, fast builds with RSpack and Jest testing support.

## Single React app

React4XP now renders pages as a single React app (aka entry), vs one React app/entry per component in version 5. This allows for a cleaner React developer experience, and more flexibility.

This also means that the  component (part of @enonic/react-components) has been changed, and is now a pure React component, handling the rendering of its sub-components directly, rather than relying on the Site engine’s placeholder and iterative rendering technique.

The latter is a breaking change. However, React4XP is still able to render multiple entries on a page (i.e. only render your parts with React4XP) if needed. Check out the [legacy mode upgrade](docs/react4xp/6.x/legacy-upgrade.md).

## Optimized asset serving

React4XP automatically hashes and serves static assets with optmized cache headers. This way, clients will only need to download files that have changed since their last visit. Assets are automatically cached in CDN if it is available.

## Component registry

React4XP uses the brand new componentRegistry (part of @enonic/react-components) to render content. The componentRegistry handles dynamic component rendering, based on what your content looks like.

The componentRegistry works in combination with the dataFetcher (part of React4XP). The dataFetcher executes server-side controllers to understand your page composition, then fetches props for each respective component to render. The result is passed to the componentRegistry for rendering.

## Response processing

React4XP still runs on top of the site engine, which means multiple XP apps can contribute to the request processing via page contributions and response processors. For instance the [SEO Metafields applications](https://market.enonic.com/vendors/enonic/seo-metafields) will inject custom tags to the HTML response - without interfering with the React4XP front-end. Applications that deliver standalone HTML may also be used - but will naturally need their own mapping.

> **Tip:** Remember, you may still bundle both CMS model and front-end in the same app.

## Booster compatible

React4XP is fully compatible with [Booster](https://market.enonic.com/vendors/enonic/booster). Booster automatically caches public and non-personalized HTML produced by React4XP. We recommend using Booster for public sites.

## Upgrading

To migrate a legacy React4XP application we have written detailed [upgrade notes](docs/react4xp/6.x/upgrade.md).
