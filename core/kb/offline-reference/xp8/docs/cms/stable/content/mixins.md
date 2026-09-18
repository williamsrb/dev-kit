<!-- src:https://developer.enonic.com/docs/cms/stable/content/mixins generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/content/mixins.md

# Mixins

Define a set of fields to be shared across content types.

## Introduction

Horizontal inheritance is a programming concept where fields can be reused across different objects. Mixins make it possible to dynamically extend existing existing content types with additional fields.

A Mixin may be added to all, or a specified list of content types. For instance, the SEO Meta fields application makes use of this, so editors may fine-tune SEO settings across all different content they produce. Also, Mixins may be explicitly enabled or made optional, so the editors may ensable or disable the mixin on a per content item basis.

In Content Studio, mixins are visualized as a separate tabs in the content editor.

## Usage

The file with mixin schema must be placed in the folder `cms/mixins/[name]` and called `[name].yaml`. For example, *site/mixins/address/address.yaml*.

address.yaml

```yaml
kind: "Mixin"
title: "Full address"
form:
  - type: "TextLine"
    name: "addressLine"
    label: "Street address"
    occurrences:
      min: 0
      max: 2
  - type: "TextLine"
    name: "city"
    label: "City"
    occurrences:
      min: 1
      max: 1
  - type: "TextLine"
    name: "zipCode"
    label: "Zip code"
    occurrences:
      min: 1
      max: 1
  - type: "TextLine"
    name: "country"
    label: "Country"
    occurrences:
      min: 1
      max: 1
```

## Activation

A mixin schema on its own is dormant — it must be registered in the application’s [CMS descriptor](docs/cms/stable/schemas/cms-descriptor.md#mixin-registration) (`cms.yaml`) before it is applied to content. The descriptor controls whether the mixin is mandatory or editor-toggleable, and whether it is restricted to specific content types via regex.

## Output

Mixin content is stored in the content under the key `x` (short for miXin).

To avoid conflict between mixins from different namespaces, the namespace is used as a prefix. For example, if you have the namespace `com.company`, with a mixin called `address` containing a field `city`, the value of that field will be stored and searchable `x.com-company.address.city`.

The JSON structure of the mixin content will look like this:

```JSON
{
  "x": {
    "com-company": {
        "address": {
            "city": "Oslo"
        }
    }
  }
}
```

> **Note:** Namespaces are transformed by replacing dots with dashes. So `com.company` becomes `com-company`. This is done to ensure that the keys are valid for content querying.

## GraphQL

When querying content with mixins via the GraphQL API, the mixin fields are available under the `x` field. For example, to query the JSON structure shown above, you would use the following GraphQL query:

```GraphQL
{
  guillotine {
    query(key: "contentid") {
      x {
      	com_company {
          address {
          	city
          }
        }
      }
    }
  }
}
```

> **Note:** Due to GraphQL field naming restrictions (`-` and `.` are not allowed), dots are replaced with underscores. So `com.company` becomes `com_company`.
