<!-- src:https://developer.enonic.com/docs/content-studio/5.x/release generated:2026-07-29T03:47:31Z format:llm-dense content-studio-5.x -->
#DOC docs/content-studio/5.x/release.md

# Release Notes

> **Tip:** Release Notes for Content Studio 4.x can be found [here](https://developer.enonic.com/docs/content-studio/4.x/release)

## Content Studio 5 Update 4

> **Important:** Content Studio 5.4 requires XP 7.16.0 or higher.

### What’s new

### Improved workflow for page customization

Several improvements have been made to make page customization more accessible, yet robust:

- The preview panel is by default always expanded in the Editor view.

- "Components" widget has been renamed to "Page" and is now always present in the Context panel when editing a page.

- Page controller or template can now be selected/changed only in the Inspect panel.

- When content preview is not available or a page template is used, a click on the Preview panel will open a context menu with "Page Settings" shortcut. Click "Page Settings" to select a page controller/template or customize the page in the Inspect panel.

|  |  |
| --- | --- |

- Detaching a content from a template now requires a confirmation to avoid accidental customization.

- "Save as Template" function is no longer available in the Inspect panel and can be executed only from the Page context menu.

### Preview mode selector in the Editor view

Preview mode selector added to the Preview panel in Content Studio v5.3 is now also available in the Page Editor. In a future version it will be possible to extend the predefined list of modes by plugging in your own preview engines with editing capabilities.

### Gallery mode in CustomSelector

[CustomSelector](https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/customselector) input type now supports gallery mode, similar to the appearance of ImageSelector’s dropdown. When enabled, the selector will display the dropdown in a gallery layout (three big images in a row), making it more suitable for selecting images.

### Schedule Publish improvements

Two major improvements have been made to the Schedule Publish functionality in the Publishing Wizard.

- It’s no longer necessary to select date/time in the "Online from" field of the Schedule form. Default value is "Now", meaning that content will go online as soon as the content is published. If a specific date/time in the future is required, it can still be set manually.

- If content has already been scheduled for publishing, then modified and needs to be republished, caption on the publish button will change from "Publish Now" to "Update Scheduled".

### Juke translation on language change

In the previous release we introduced integration with Juke AI Translator to provide AI-powered translation when localizing content in a layer. In this release we have extended this functionality to also provide automatic translation when changing the language of existing content in a regular project, not a layer.

After changing the language of content that has text fields, Content Studio will now suggest translating all text fields to the new language using Juke AI Translator (assuming it’s installed).

> **Note:** Translation will only be suggested when changing language in the content edit view.

### Layers widget

[Layers Widget](docs/content-studio/5.x/layers.md#layers_widget) has been improved to better visualize placement of the content in the project hierarchy. By default, only direct ancestors and descendants of the current layer are shown.

To see all layers where the content exists, click "Show all" button at the bottom of the widget. This will open a modal dialog with the full overview of content placement in the project hierarchy.

### Version History improvements

Selection of two versions for comparison in the Version History panel is now done with checkboxes, instead of clicking the "Compare" icon next to each version. This makes it more obvious which versions are going to be compared.

Long lists of versions in the Version History panel have been optimized for a faster load.

### Archive comment

When archiving content, it’s now possible to provide an optional comment in the Archive dialog explaining the reason for archiving. The comment will be visible in the Version History panel.

### Language plugin in HtmlArea

A new Language plugin has been added to the [HtmlArea](https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/htmlarea) input type. This plugin allows setting the `lang` attribute on selected text inside the editor to correctly present content written in multiple languages to screen readers ([WCAG specs](https://www.w3.org/TR/UNDERSTANDING-WCAG20/meaning-other-lang-id.html)).

> **Note:** Contact a developer to help you enable this plugin by configuring an HtmlArea input type in content type schema.

### Notification about a new release

Content Studio will now notify users with Administrator and Content Manager roles about availability of a new feature release (not patch releases). A non-intrusive banner will be briefly shown at the bottom of the Content Studio window, with a link to the release notes page.

> **Note:** Once the user clicks on the close icon to dismiss the banner, it will not be shown again until a new feature release is available.

### Other improvements

- Websocket stability has been improved.

- A lifetime of warning and error notifications has been increased to give users more time to read them. Also, a notification will now only be dismissed when the user clicks the close icon, not anywhere on the notification itself.

- When the current user didn’t have READ permissions for a selected content in Content Selector, the placeholder was displayed saying that the item is not available. Now, a more descriptive message is shown saying that the user doesn’t have permissions to view the item, which helps distinguish the lack of permissions from actual missing items.

## Content Studio 5 Update 3

> **Important:** Content Studio 5.3 requires XP 7.15.0 or higher.

### What’s new

### Juke AI support

Content Studio has been adapted to support ecosystem of Juke applications, new AI-powered extensions that enable high-level assistance for content editors. In this release Content Studio provides integration with Juke apps responsible for content localisation ([Juke Translator](docs/content-studio/5.x/layers.md#_ai_translation)) and content creation ([Juke Content Operator](docs/content-studio/5.x/ai.md)).

> **Note:** Juke apps are not built into Content Studio and need to be installed and configured individually. Contact us if you want to enable Juke AI support in your Content Studio.

> **Important:** Enonic does not store any conversations or data processed by Juke AI. During conversations, the data is sent to the Google Vertex service and the response is displayed directly in Content Studio. Once the browser tab is closed or refreshed, the conversation thread will be gone.

#### Juke Translator

With this application installed, Content Studio will suggest translating content localised in a layer, to the language of the layer. After clicking "Localise" for an inherited content in a layer, user will see a dialog suggesting automatic translation of all text fields in the localised content to the language of the layer.

It’s possible to provide custom instructions for the Juke AI to follow when translating the content. If you need to provide some context on a regular basis, add "Juke Translator" to your site and set instructions via site config, then Juke will reuse them for every translation.

#### Juke Content Operator

Help-text icons for inputs in the Content Form have been replaced with icons to require assistance from the Juke AI Content operator for this specific field. As of now, Content Operator provides assistance only for inputs of type TextLine, TextArea and HtmlArea.

> **Tip:** Help-text for inputs can still be toggled by using the help-text icon in the content form toolbar.

> **Tip:** To provide custom instructions for the Juke AI to follow when assisting with content creation, add "Juke Content Operator" to your site and set instructions via site config.

### Preview mode

#### Mode selector

It’s now possible to select preview mode inside the Preview panel. Currently available built-in modes are: Media, Enonic rendering and JSON. Default selection is "Automatic" which will automatically find and use the first mode that supports preview of current content.

> **Tip:** In future versions it will be possible to add custom preview modes.

Read more about content preview modes in the [Content Navigator documentation](docs/content-studio/5.x/navigator.md#preview_panel).

#### Emulator

Device emulator selector - that used to be a widget inside Context Panel - has been turned into selector inside the Preview panel’s toolbar.

#### Preview button

Preview button was moved from the Content Navigator’s toolbar to the Preview panel’s toolbar. It will still open preview of currently selected content in a new browser tab, but preview in the new tab will use the currently selected mode (f.ex. JSON).

### Edit text in the Inspect panel

It’s now possible to edit contents of a Text component directly in the Inspect panel on the right.

### Support for webp and avif

Content Studio now supports upload and preview of images in webp and avif format. Image modifications are not yet supported.

### Accessibility improvements

Several improvements have been made to make Content Studio more accessible and comply with WCAG 2.1 standards:

- Focused elements are now highlighted with a blue border

- Keyboard navigation has been improved

- Toolbars and their child elements are now focusable and can be navigated with arrow keys, according to WCAG 2.1 standards

- Most of the elements received proper ARIA roles and labels

### Other improvements

- If a page component (part or layout) provides page contributions, Content Studio will automatically inject them into the page editor, so it’s no longer required to refresh the page for the contributions to start working.

- Tag input will now parse a string pasted into it and create tags from the parsed values.

- We have strengthened Content Security Policy (CSP) even more by disabling `unsafe-eval` in `script-src` (read more [here](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/script-src#unsafe_eval_expressions)). Please test and adapt your applications accordingly.

## Content Studio 5 Update 2

> **Important:** Content Studio 5.2 requires XP 7.14.1 or higher.

### What’s new

### Project graph

By selecting "Projects" in the Content Studio’s "Settings" module it’s now possible to see a visualised graph of existing content projects and their relations.

### Project Wizard improvements

#### Preset parent project

If an existing project is selected in the Project tree when the "New" button is clicked, the Project Wizard will create a layer of the selected project and set up synhronisation of data in the layer with its parent project.

#### Removed type selection

Before this release, users had to explicitly select whether they are about to create a project or a layer. This requirement has been removed. If a parent project is selected on the first step of the Wizard, a layer will be created and set up to inherit data from the selected project. Otherwise, a regular project will be created.

#### Parent project apps

A layer will always inherit applications from its parent project, even though it was not obvious from the UI before this release. "Applications" step of the "Project Wizard" has been changed to automatically display applications inherited from the parent project (if any), with no option to remove them. Other applications can be added to the layer in addition to the inherited ones.

The settings form of an existing layer has also been fixed accordingly.

In the screenshot below, the top two applications were inherited from the parent project, while the bottom one was added manually.

### Reference check in the Unpublish Wizard

The Unpublish Wizard will now check if any of the content items to be unpublished are referenced by other *published* content items. If there are inbound references, the user will be warned and asked to confirm the unpublish operation.

### Decorative images

A new "Accessibility" section in the [Insert/Edit Image dialog](docs/content-studio/5.x/editor/rich-text-editor.md#insertedit_image) of Rich Text editor allows the setting of decorative images as such. Decorative images are used for styling purposes only and meant to be skipped by screen readers, as opposed to images with meaningful alt text.

### Default Online From time

Default Online From time in the Publishing Wizard can now be configured in Content Studio’s [config file](docs/content-studio/5.x/config.md#default_online_from_time). If no config is set, the default time will be set to 12:00.

### Page Components view

Styling of regions inside the Page Components view has been changed to make regions take less space and attention away from the main page components. Region names are now capitalized.

### Other improvements

#### Performance

Preview and Page Editor panels will no longer be refreshed whenever content is published or unpublished.

#### Soft-hyphen in the Rich Text Editor

Soft-hyphen character `­` added to Rich Text Editor’s "Special chars" dialog.

#### Email sender

Before this release, email notifications for [issues](docs/content-studio/5.x/issues.md) created in Content Studio used the current user’s email address in the sender field. A new [config property](https://developer.enonic.com/docs/xp/stable/deployment/config#mail) is implemented in XP 7.14.1 which can be used to configure default email sender for emails sent by XP. If properly configured, the sender field in the email notifications sent for issues in Content Studio will be set to the configured email address.

#### eXtra Data

Layout and behaviour of optional X-Data sections in the Content Form have been changed. `+` icon is now right-aligned and transforms to `x` icon whenever the X-Data is active.

## Content Studio 5 Update 1

> **Important:** Content Studio 5.1 requires XP 7.13.0 or higher.

### What’s new

### Improved move operation

- Move Content dialog: New "Project root" node on top of the content tree to make it more obvious how to move content to the root. Previously one had to click "Move" button with no target content selected.

- Move Content dialog: "Move" button is disabled until new parent node is selected.

- It’s now possible to move content from inside the Content Editor

- Notification about successful move includes the new parent’s path which can be clicked to locate and expand the new parent inside the Content Navigator.

### Improved auto-exclusion of optional dependencies

The new mode for auto-exclusion of optional dependencies in the Publishing Wizard, originally introduced in Content Studio 5.0, has been improved to not hide the auto-excluded dependencies but keep them visible (while still excluded) in the list.

> **Tip:** This mode can be turned on in Content Studio’s [config file](docs/content-studio/5.x/config.md#exclude_optional_dependencies)

### Export of search results

Search results produced by Content Navigator’s [Search Panel](docs/content-studio/5.x/navigator.md#search_panel) can now be exported into a CSV file using the download icon next to the Search Panel’s free-text search field. The file will contain the following fields: **Id**, **Path**, **Creator**, **Modifier**, **Created**, **Modified**, **Owner**, **Content Type**, **Display Name**, **Language**, **Published From**, **Published Until**, **First Published**.

### New Find/Replace dialog in Rich Text Editor

The old [Find/Replace dialog](docs/content-studio/5.x/editor/rich-text-editor.md#findreplace) in the Rich Text Editor that used to cover the text it was searching inside, has been replaced with the new inline dialog that allows editor to use the search/replace functions without blocking the source text.

### Locked path for published content

Previously, the editor had to click the "lock" icon next to the locked path input inside the Content Editor, in order to rename a published content. That icon is now removed and the path itself has to be clicked to open the Rename content dialog.

### Other improvements

- Improved responsiveness in the Content Navigator

- Improved synchronisation between the Content Form’s [Page Components tree](docs/content-studio/5.x/editor/content-form.md#page_components_tree) and components inside the [Page Editor](docs/content-studio/5.x/editor/page-editor.md)

- When a published item has been first moved, then modified its status will be shown as `Moved, Modified` (previously just `Moved`)

- "Show changes" link for comparison of publishing modifications is replaced with an icon

- New icon for switching the project context

## Content Studio 5

> **Important:** Content Studio 5.0 requires XP 7.13.0 or higher.

### What’s new

### Default Content Project is hidden by default

Default Content Project is no longer available in Content Studio without tweaking the config file.

If you need the Default project (for example, you already have content in it and want to continue working with it after upgrading to Content Studio 5), enable it via Content Studio’s [config file](docs/content-studio/5.x/config.md#enable_default_content_project).

### Page Components View

Page Components View, which used to be a floating modal window inside Page Editor, is now made a part of the [Content Editor form](docs/content-studio/5.x/editor/content-form.md#page_components_tree). It will be automatically undocked whenever the Content Form is collapsed.

### Publishing Wizard improvements

It’s now possible to auto-exclude optional dependencies of selected content from publishing batch via Content Studio’s [config file](docs/content-studio/5.x/config.md#exclude_optional_dependencies).

### Call links in the Insert Link dialog

A new URL type option `Tel` in the Rich Editor’s "Insert Link" dialog enables adding call links.

### Other improvements

- Preview panel won’t be auto-expanded for a site until there’s at least one controller from apps assigned to the site.

- Content Selector displays status of selected content items.

- Widgets inside Content Studio have been localised to other languages than English
