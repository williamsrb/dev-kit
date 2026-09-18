<!-- src:https://developer.enonic.com/docs/content-studio/stable/workbench/contextpanel generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/workbench/contextpanel.md

# Context panel

The **Context panel** is the multi-function column on the right of the [Navigator](docs/content-studio/stable/workbench/navigator.md) and the [Editor](docs/content-studio/stable/editor.md). It hosts a set of **widgets** — small tools that act on the currently selected content item. Widgets can be built-in, shipped by [Content Studio+](https://market.enonic.com/vendors/enonic/content-studio-plus), or contributed by any installed application.

The panel is toggled open and closed with the icon next to the Action-menu button in the Navigator, or with the cog icon on the right of the editor toolbar in the Editor.

## Widget selector

The dropdown at the top of the panel lists the available widgets: the built-ins appear first, followed by widgets from installed applications. A filter field at the top narrows the list by keyword.

## Built-in widgets

- [Details](docs/content-studio/stable/workbench/contextpanel/details.md) — basic properties of the selected content item (display name, path, status, permissions, properties, schedule, attachments).

- [Dependencies](docs/content-studio/stable/workbench/contextpanel/dependencies.md) — inbound and outbound references between the item and other content.

- [Version history](docs/content-studio/stable/workbench/contextpanel/versions.md) — every version of the selected item; lets you compare or revert.

- [Components](docs/content-studio/stable/editor/page-editor.md#_components_widget) — the page-building tool that appears in the Editor for renderable content.

## Content Studio+ widgets

The following widgets are contributed by [Content Studio+](https://market.enonic.com/vendors/enonic/content-studio-plus):

- [Layers](docs/content-studio/stable/projects/layers.md#layers_panel) — shows the status of a content item across every layer in the system.

- [Variants](docs/content-studio/stable/workbench/contextpanel/variants.md) — creates and manages A/B variants of the selected item.

## Contributing a widget

The Context panel is **pluggable**: any installed application can contribute a widget that appears in the widget selector.

See the [Context panel extension reference](https://developer.enonic.com/docs/code/stable/web/extensions/contextpanel) for the descriptor format, lifecycle, and implementation details.
