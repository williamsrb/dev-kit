---
name: apply-react4xp-practices
description: "React4XP 6 conventions: naming, XML schemas, TypeScript, processors, component registration. Use when creating or editing Enonic parts, layouts, content types, x-data, mixins, or macros. | recommendedRole: implement | aliases: enonic-react4xp-best-practices, enonic-r4xp-conventions."
metadata:
  recommendedRole: implement
  aliases: enonic-react4xp-best-practices, enonic-r4xp-conventions
  cliDependencies:
    required: [agentctl, rg, xmllint]
    optional: [xmlstarlet, yq]
---

## Cursor IDE

Adapted from [git.example.com/group/enonic-skills](https://git.example.com/group/enonic-skills). Read reference files under `references/` with the **Read** tool before generating or editing Enonic React4XP code.

# Enonic React4XP 6 Best Practices

Read `references/general-conventions.md` first, then only the matching type file. Do not load every reference.

| Task involves | Read |
|---------------|------|
| Part | `general-conventions.md`, `parts.md`, `fields-processing.md` |
| Layout | `general-conventions.md`, `layouts.md`, `fields-processing.md` |
| Content type or schema | `content-types.md`, `mixins.md` |
| X-data | `x-data.md`, `mixins.md` |
| Macro | `macros.md`, `general-conventions.md` |
| Any new component | `general-conventions.md` + type-specific file |
| Descriptor XML | `descriptor-structure.md` |
| Background tasks | `development-guidelines.md` |

