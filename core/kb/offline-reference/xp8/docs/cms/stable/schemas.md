<!-- src:https://developer.enonic.com/docs/cms/stable/schemas generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas.md

# Schema system

Schemas are the heart of the CMS, enabling you to express your content model as code.

## Introduction

Schemas are used to define various editorial elements within the CMS. Schemas may contain a [Form](docs/cms/stable/schemas/forms.md) which allow you to declare custom data structures. Every schema lives in a [namespace](docs/cms/stable/schemas/namespaces.md) that scopes its package and prevents collisions between independent providers.

The available schema kinds are:

- [CMS](docs/cms/stable/schemas/cms-descriptor.md) (Shared configuration and settings)

- [Content Types](docs/cms/stable/content/content-types.md)

- [Mixins](docs/cms/stable/content/mixins.md)

- [Form Fragments](docs/cms/stable/schemas/form-fragments.md)

- [Pages, Parts and Layouts](docs/cms/stable/pages.md)

- [Macros](docs/cms/stable/richtext/macros.md)

- [Styles](docs/cms/stable/richtext/styles.md)

## Schema deployment

Schemas are managed as code, and deployed to Enonic XP via Enonic apps. When an application gets installed, the schemas are registered in the system, and instantly reflected in Content Studio and related APIs.

See the [schema packaging and deployment reference](docs/code/stable/schemas.md) in the Enonic Development Kit docs for project layout, build configuration, and registration details.

## Descriptor

Schemas are defined using YAML files, and registered with a unique identifier : (i.e. "com.example:article")

Sample schema definition

```yaml
kind: “ContentType”  (1)
title: “Person”  (2)
displayNameLabel: “Full Name”  (3)
form: []  (4)
```

| ****1** | [Kind](#kinds) - i.e. "ContentType", "Mixin" etc. |
| --- | --- |
| ****2** | Title - Human readable schema name. |
| ****3** | [Configuration](#configuration) - Validated fields for each schema kind |
| ****4** | [Form](docs/cms/stable/schemas/forms.md) - Optional form that declares a custom data structure for the schema. |

## Schema localization

You may provide [translations](docs/cms/stable/schemas/i18n.md) for your schemas in multiple languages for better usability in Content Studio.
