<!-- src:https://developer.enonic.com/docs/content-studio/stable/workbench/contextpanel/variants generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/workbench/contextpanel/variants.md

# Variants

> **Note:** **Content Studio+ feature.** The Variants widget is part of the [Content Studio+](https://market.enonic.com/vendors/enonic/content-studio-plus) subscription.

Variants are essentially slightly modified copies of a content item used for comparing them against each other to determine which one performs better for end user (A/B Testing).

Using "Variants" widget provided by **Content Studio+**, user can create variants of a specific content item, duplicate them (make copies of variants), then use URLs of variants in a 3rd party A/B Testing tool. Variants can be managed (modified, published, duplicated, deleted etc.) just as regular content items.

To create a new variant, select a content item in the [Navigator](docs/content-studio/stable/workbench/navigator.md) grid, then open the "Variants" widget in the [Context panel](docs/content-studio/stable/workbench/contextpanel.md) on the right-hand side (if you cannot find it then you probably don’t have **Content Studio+** installed) and click "**Create Variant**" button.

This will open a new modal dialog for specifying name of a variant, suggesting "*variant-1*", "*variant-2*" etc., based on how many variants of the item already exist. A new name will be verified for uniqueness. The rest of the properties will be copied from the original item.

After a new variant is created, it will be placed under the original item in the Navigator grid and displayed in the "Variants" widget under the original item. Each variant has a context menu with "**Edit**" and "**Duplicate**" options.
