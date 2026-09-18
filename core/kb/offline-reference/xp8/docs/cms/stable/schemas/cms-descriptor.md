<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/cms-descriptor generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/cms-descriptor.md

# CMS descriptor

The CMS descriptor (`cms.yaml`) marks a schema package as a CMS package and exposes its schemas for assignment to content projects and sites.

## Introduction

`cms.yaml` is the package-level descriptor for the CMS. Its presence is what makes a schema package **assignable** to a content project or a site — without it, the schemas it ships will not appear in CMS contexts. The descriptor also lets the developer declare:

- A **configuration form** shown to administrators when the package is added to a project or site, capturing per-instance settings.

- **Mixins** that should be activated on content within the assigned scope, with optional content-type filtering.

> **Note:** Schema packages are currently delivered as Enonic XP applications. The descriptor lives at `src/main/resources/cms/cms.yaml` inside the app, and the app name serves as the [namespace](docs/cms/stable/schemas.md#namespaces). See [Deployment](#deployment) below for packaging and registration details.

## Descriptor

```yaml
kind: "CMS"  (1)
form:  (2)
  - type: "TextLine"
    name: "apiKey"
    label: "API key"
    occurrences:
      min: 1
      max: 1
mixins:  (3)
  - name: "address"
```

| ****1** | **kind** (required) Identifies this as a CMS package descriptor. Without `kind: "CMS"`, the file is ignored and the package will not appear as installable in Content Studio’s project or site app-picker. |
| --- | --- |
| ****2** | **form** (optional) A [Form](docs/cms/stable/schemas/forms.md) definition rendered when an administrator adds the package to a project or site. The submitted values are persisted alongside the assignment and are available at runtime — useful for per-instance settings such as API keys, feature flags, or endpoint URLs. |
| ****3** | **mixins** (optional) Registers [mixins](docs/cms/stable/content/mixins.md) to be activated on content within the assigned scope. See [Mixin registration](#mixin-registration) below for filtering and optional-mode variants. |

## Mixin registration

Mixins declared under `mixins:` are applied by default to **all** content types within the project or site that hosts the package. Two attributes refine that behaviour:

allowContentTypes

A regular expression matched against the qualified content-type name. Only matching content types receive the mixin.

optional

When `true`, the mixin is not added automatically — editors must enable it per content item from within the Content Wizard.

```yaml
kind: "CMS"
mixins:
  - name: "my-mixin-1"  (1)
  - name: "my-mixin-2"  (2)
    allowContentTypes: "^(?!base:folder$).*"
  - name: "my-mixin-3"  (3)
    allowContentTypes: "portal:site"
    optional: true
```

| ****1** | Activated for all content types, no opt-out. |
| --- | --- |
| ****2** | Activated for all content types except `base:folder`. |
| ****3** | Available to `portal:site` content only, and only when an editor explicitly enables it. |

See [content type filtering modes](docs/cms/stable/schemas/form-items/contentselector.md#allowContentType) for the full regex syntax accepted by `allowContentTypes`.

## Deployment

Schema packages are deployed to Enonic XP via Enonic apps. The CMS descriptor and all schemas it references live in the app’s `src/main/resources/cms/` directory, and are registered automatically when the app is installed — instantly reflected in Content Studio and the headless APIs.

See the [schema packaging and deployment reference](docs/code/stable/schemas.md) in the Enonic Development Kit docs for project layout, build configuration, and registration details.

> **Note:** An app that also contributes page components ships a separate `site.yaml` descriptor alongside `cms.yaml`. `site.yaml` belongs to Enonic’s app-rendering paradigm (parts, layouts, controllers, page contributions) and is documented in the [Enonic Development Kit](https://developer.enonic.com/docs/code) docs.
