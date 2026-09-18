<!-- src:https://developer.enonic.com/docs/content-studio/5.x/editor/page-editor generated:2026-07-29T03:47:31Z format:llm-dense content-studio-5.x -->
#DOC docs/content-studio/5.x/editor/page-editor.md

# Page Editor

Page Editor is a modifiable preview of the content page that will open automatically when a content is created or edited. It is used in conjunction with the [Context Panel](docs/content-studio/5.x/editor/context-panel.md) to add, remove, and move components around the page with drag and drop. The page editor can be toggled on/off with the icon on the far right of the toolbar.

## Preview

Page Editor panel will not display any preview if there is no template or controller that is capable of rendering the content. This could be because no application is assigned to the site that supports the content type, or because the application does not have any templates or controllers defined for it.

To enable the preview, do the following:

- Assign an application to the site that provides rendering for the selected content.

- Click the Visual Editor panel and select "Page Settings" from the menu (or manually open the Page widget from the Context Panel).

- If there are no applications assigned to the site, or none of the assigned applications has page controllers and no page templates exist on the site, the Page widget will say "*No page templates or components available*". Otherwise, you will see a dropdown with the list of available controllers and templates.

Default selection in the dropdown is "Automatic" which means that the best suitable [page template](docs/content-studio/5.x/content-types.md#page_templates) will be used for rendering the content. If there’s already a template that matches the content type, preview should automatically start working at this point. Otherwise, you will have to select a specific controller from the list.

## Editor panel

The content that is using a template will be locked for editing. In this case, a click on the pane will display the "Page Settings" shortcut to open the "Page" widget where you can unlink the content from the template by clicking the "Customize Page" button (requires additional confirmation).

If the content is not using a template, its components can be selected inside the Editor panel (or in the Page Components tree). This will highlight the selected component and show its configuration in the Inspect panel of the Page widget on the right. Right-clicking a component will open a context menu with various actions that can be performed on the component. These options may include **Select parent**, **Insert** another component, **Inspect** its configuration, **Reset** the component’s configuration, **Remove** the component, **Duplicate** it, and **Save as fragment**.

For the **Fragment** component, the last action will be replaced with the **Detach from Fragment** and the **Edit** action will be added.

## Preview modes

Similar to the preview mode selector in the Navigator’s [Preview panel](docs/content-studio/5.x/navigator.md#preview_panel), Page Editor has its own preview mode selector located in the top-right corner of the panel. Predefined modes are **Automatic** (default, the best suitable mode), **Media**, **Enonic rendering**, and **JSON**.

## Page widget

Page Editor adds a new Page widget to the widget list in the Context Panel. This widget can be used to switch between different page templates and controllers for the current content and manage components on the page.

## Page Components tree

When the Content form is collapsed (with the icon in the menu toolbar), the Page Components tree will be docked inside the vertical menu toolbar, left-bottom corner.

Clicking the icon will open the view in floating mode, over the Editor panel.
