<!-- src:https://developer.enonic.com/docs/react4xp/stable/release generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC docs/react4xp/stable/release.md

# React4XP 7 Release notes

New features and improvements since version 6

## XP 8 support

React4XP 7 targets XP 8, which is a major platform release that, among other things, replaces XML component descriptors with YAML, introduces a Gradle settings plugin with a dependency catalog, and requires Gradle 9. React4XP 7 aligns with all of this out of the box.

> **Note:** React4XP 7 requires Enonic XP 8. If you are still on XP 7, stay on React4XP 6.

## YAML descriptors

Component descriptors (site, parts, layouts, pages, admin tools and so on) are now written in YAML using the new `kind:` format, replacing the previous XML descriptors. CMS schemas and their implementations also move from the `site/` folder to `cms/`.

## New server build with tsdown

Server-side TypeScript is now compiled with [tsdown](https://tsdown.dev) (powered by SWC), giving faster and simpler server builds. React entries (`.tsx`) are still compiled by React4XP with Rspack.

## Native CSS with Rspack

React4XP 7 uses Rspack’s native CSS support. CSS Modules work out of the box for `**.module.css**`** and ``**`.module.scss` files, and the old `mini-css-extract-plugin` setup is gone.

## Unified Enonic types

React4XP 7 builds on `@enonic-types/core`, delivered through `@enonic-types/global` 8. The `Request` type now comes from `@enonic-types/core` instead of `@enonic/js-utils`.

## Modernized toolchain

The build runs on Gradle 9 with the XP settings plugin and the `xplibs` dependency catalog, alongside current Node and npm. See the upgrade notes for the exact versions.

## Still included from version 6

The version 6 architecture carries over unchanged: a detached front-end, a single React app per page, the componentRegistry and dataFetcher rendering model, hashed and cache-optimized asset serving, and full [Booster](https://market.enonic.com/vendors/enonic/booster) compatibility.

## Upgrading

To migrate an existing React4XP application, follow the detailed [upgrade notes](docs/react4xp/stable/upgrade.md).
