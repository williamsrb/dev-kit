<!-- src:https://developer.enonic.com/docs/content-studio/stable/workbench generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/workbench.md

# Workbench

The **Workbench** is the application shell of Content Studio. It has three parts: a **project bar** across the top, a **menu bar** on the left, and a **main panel** that fills the rest.

> **Tip:** The [Editor](docs/content-studio/stable/editor.md) is not part of the Workbench — it opens in a separate browser tab.

## Project bar

The horizontal bar across the top of the window. It carries application-wide controls that are not specific to any single menuitem:

- The **project context selector** on the left — switches between the projects and layers the current user has access to. Every menuitem (except Settings, see below) inherits the selected project as its context.

- An **open issues** indicator showing the number of unresolved [issues](docs/content-studio/stable/issues.md) in the current project, with a dropdown to jump into them.

- The current user’s avatar and the XP admin menu on the right.

## Menu bar

The vertical strip on the left lists the available **menuitems**: top-level views contributed by Content Studio or by an installed application. Clicking an icon swaps the [main panel](#main_panel) to that menuitem’s view.

- **Navigator** — the built-in default, anchored at the top of the menu bar. The content tree, search, and per-content actions. See [Navigator](docs/content-studio/stable/workbench/navigator.md).

- **Settings** — anchored at the bottom-left, set apart from the regular menuitem stack. Unlike the others, Settings is **not** scoped to the currently selected project — it manages all projects and layers. See [Settings](docs/content-studio/stable/workbench/settings.md).

Additional menuitems are contributed by installed applications and appear in the stack between Navigator and Settings. The two most common:

- **Archive** — browse, restore, and permanently delete archived content. Contributed by [Content Studio+](https://market.enonic.com/vendors/enonic/content-studio-plus). See [Archive](docs/content-studio/stable/workbench/archive.md).

- **GraphQL Playground** — interactive query console for the Guillotine API. Contributed by [Guillotine](https://market.enonic.com/vendors/enonic/guillotine).

### Contributing a menuitem

Any installed application can add a menuitem to the menu bar. The icon and view appear when the app is installed in the current project.

See the [menuitems extension reference](https://developer.enonic.com/docs/code/stable/web/extensions/menuitem) for the descriptor format, lifecycle, and implementation details.

## Main panel

The remaining space is the main panel — the surface controlled by the active menuitem. The Navigator splits it into a toolbar, search panel, content tree, [Preview](docs/content-studio/stable/workbench/preview.md), and [Context panel](docs/content-studio/stable/workbench/contextpanel.md); other menuitems arrange the panel differently.

Two of those panels — [Preview](docs/content-studio/stable/workbench/preview.md) and [Context panel](docs/content-studio/stable/workbench/contextpanel.md) — appear inside multiple menuitem views (Navigator, Archive) and also inside the [Editor](docs/content-studio/stable/editor.md). Their behaviour and extension models are shared across surfaces, which is why they are documented on their own pages.
