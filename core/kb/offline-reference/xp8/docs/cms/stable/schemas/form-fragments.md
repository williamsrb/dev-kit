<!-- src:https://developer.enonic.com/docs/cms/stable/schemas/form-fragments generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/schemas/form-fragments.md

# Form Fragments

Reuseable form definitions

## Introduction

If you find yourself in need of repeating the exact same form pattern across different schemas, form fragments may be what you’re looking for.

This is a special kind of schema, containging only a single . By referencing a form fragment from another schema, you pull the fragment form definition into the referencing schema’s form.

## Usage

Like other schemas, Form fragments are defined in YAML.

Sample form fragment

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

Below is an example of a simple content type that references the address mixin above.

The mixin form fields will simply be included into the final content type schema.

```yaml
kind: "ContentType"
title: "Using mixins"
form:
  - type: "TextLine"
    name: "firstName"
    label: "First Name"
  - include: "address"
```

## Limitations

Form fragments are only supported for content schemas, and may not be used in other schema contexts such as identity providers and tasks.
