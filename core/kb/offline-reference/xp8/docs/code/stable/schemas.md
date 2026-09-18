<!-- src:https://developer.enonic.com/docs/code/stable/schemas generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/schemas.md

# Content schemas

Desciption of how to ship your **CMS schemas** as code as part of your Enonic app

## Introduction

The CMS schemas control your content model. The schemas descriptors are writte in YAML. In this example, we show how to bundle and deploy schemas to XP as part of an app.

> **Note:** Visit the [CMS docs](https://developer.enonic.com/docs/cms/xp8/schemas) for details on content modeling.

You may bundle schemas in any Enonic app. [The Vanilla starter](https://market.enonic.com/starters/vanilla-starter) is a minimalistic approach.

Create a new app using Enonic CLI:

```
enonic create -r starter-vanilla com.company.myapp
```

> **Note:** Choose the app name carefully. It becomes part of the schema namespace and is awkward to change later. The canonical format is `com.company.myapp`, but you can choose any unique string. Avoid generic names like `schemas` or `content` that may conflict with other apps.

## How it works

A single app may contribute any combination of:

Content types

Define the structure of editorial content (articles, products, media types, …).

Mixins

Extra metadata attached to existing content types (formerly known as `x-data`).

Form fragments

Reusable pieces of a content form, includable from other schemas.

Components

Pages, parts, and layouts for building landing pages

Macros

Custom rich-text macros invocable inside HtmlArea fields.

Styles

Rich-text styling extensions.

The schemas are registered when the app is installed and become available immediately in Content Studio and the content APIs. Within their kind, each schema gets registered by namespace and schema name as follows: `:` (for example, `com.example.myapp:article`).

## File structure

Schemas must be placed under `src/main/resources/cms/`, with one folder per kind:

```text
src/main/resources/
  cms/
    cms.yaml                       (1)
    content-types/
      article/
        article.yaml
        article.svg                (3)
    mixins/
      seo/
        seo.yaml
    form-fragments/
      address/
        address.yaml
    pages/
      default/
        default.yaml
    parts/
      hero/
        hero.yaml
    layouts/
      two-col/
        two-col.yaml
    macros/
      embed/
        embed.yaml
```

| ****1** | `cms.yaml` — the **app’s CMS descriptor**. Used to activate mixins on existing content types and to declare app-level form references. See [The `cms.yaml` app descriptor](#cms-yaml). |
| --- | --- |
| ****2** | Optional sibling icon, displayed in Content Studio. |

The folder name, file name, and the schema’s referenceable name must match: `cms/parts/hero/hero.yaml` is will be available in the system as `:hero`. Choose names carefully — they end up in stored content data and are awkward to change later.

## A content type, end to end

The descriptor is YAML. Here is a minimal content type, using the canonical shape from the [CMS content-types reference](https://developer.enonic.com/docs/cms/xp8/content/content-types):

src/main/resources/cms/content-types/person/person.yaml

```yaml
kind: "ContentType"
title: "Person"
displayNameLabel: "Full Name"
description: "Create a new person"
superType: "base:structured"
abstract: false
final: true
allowChildContent: true
allowChildContentType:
  - "base:folder"
  - "article-*"
form:
  - name: "fullName"
    type: "TextLine"
    label: "Full name"
    occurrences:
      minimum: 1
      maximum: 1
  - name: "bio"
    type: "TextArea"
    label: "Biography"
```

> **Note:** The full set of form items is documented in the [CMS forms reference](https://developer.enonic.com/docs/cms/xp8/schemas/form-items).

## The `cms.yaml` app descriptor

`cms/cms.yaml` is the app-level CMS descriptor. Two roles:

- **Activate mixins.** A mixin you ship in `cms/mixins//` is dormant until you opt in here. List it under `mixins:` to make it active for content types in this app.

- **Declare an app-level form.** Lets your app’s site configuration form be edited in Content Studio.

src/main/resources/cms/cms.yaml

```yaml
kind: "CMS"
mixins:
  - name: "seo"
form:
  - name: "tracking-id"
    type: "TextLine"
    label: "Analytics tracking ID"
```

Without the `mixins:` entry, the `seo` mixin is bundled but not attached to anything.

## Deployment

Nothing extra is required. When the app is installed (or hot-deployed during development by dropping the JAR into XP’s `deploy/` folder), XP scans the bundle, registers every schema under the app’s key, and Content Studio refreshes immediately. Removing the app removes the schemas; redeploying a new bundle replaces the previous registration.

There is no separate "publish schemas" step. The bundle **is** the source of truth.

## References

- [CMS schemas reference](https://developer.enonic.com/docs/cms/xp8/schemas) — the schema language, field types, and per-kind documentation.

- [CMS documentation](https://developer.enonic.com/docs/cms/xp8) — content modelling, queries, and runtime APIs.

- [Starters](docs/code/stable/tooling/starters.md) — folder layout for the rest of an Enonic app.

- [Sites](docs/code/stable/web/sites.md) — wiring page/part/layout schemas to rendering implementations.
