<!-- src:https://developer.enonic.com/docs/cms/stable/pages/filtering generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/pages/filtering.md

# Component filtering

Optionally limit which pages a component can be placed on.

## Usage

Some components are only relevant for selected content types. To limit which pages a component may be placed on, add an allow configuration to it:

Limit part to specific content types

```yaml
kind: "Part"
title: "My article part"
form: []
allowOnContentType:
  - "my.cool.app:my-cool-type"
  - "${app}:article*"
```

You may also use regular expressions:

Advanced example using regular expression

```yaml
kind: "Part"
title: "My article part"
form: []
allowOnContentType:
  - "^(?!.*[:]post$).*$"
```

> **Note:** This restriction is only implemented in Content Studio, and will not be enforced by the API.
