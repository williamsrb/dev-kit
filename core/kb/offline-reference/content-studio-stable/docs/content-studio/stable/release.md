<!-- src:https://developer.enonic.com/docs/content-studio/stable/release generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/release.md

# Content Studio 6 Release Notes

Release notes for Content Studio 6 - June 2026.

> **Important:** Content Studio 6 requires Enonic XP 8.0 or newer.

## Content Studio 6.0

This is a major release with significant improvements and new features. The release focuses on modernizing the user interface, improving the preview system, and rebuilding the underlying architecture for better performance and extensibility.

### Revamped UI

Content Studio 6 features a completely redesigned and re-built - based on the [Enonic UI design system](https://enonic.github.io/npm-enonic-ui/), with a modernized architecture and a compelling new look and feel. The new interface is more intuitive, responsive, and accessible, with improved workflows and a more consistent design across the application.

Here are some of the changes:

- **Icons** — updated icons throughout the application, providing a more modern and cohesive look.

- **Consistency** — a more consistent design across the application, with improved typography, spacing, and visual hierarchy

- **Less clutter** — a cleaner interface with less visual clutter, making it easier to focus on the task at hand.

- **Dark mode** — a new dark mode for the user interface, providing a more comfortable experience in low-light environments.

- **Accessibility** — improved accessibility across the application, with better keyboard navigation, screen reader support, and color contrast for WCAG 2.1 compliance.

- **Status indicators** — Simplified online/offline status indicators across the application

- **Diff status** — clearer indicators for changes, used in publishing wizard and version history.

- **Polished dialogs** — redesigned dialogs with improved layout and clearer actions, including multi-step wizards.

- **Improved drag-and-drop** — improved drag-and-drop support across the application, including visual feedback and support for dragging content between different areas of the application.

- **Gallery mode** — has been redesigned with a cleaner layout and larger thumbnails, making it easier to browse and find content items.

- **Validation handling** — improved validation feedback in forms, with clearer error indicators, as well as bubbling validation errors to the top of the form for better visibility.

### Permissions

Permissions wizard has been udpated to reflect the improvements for permissions handling in XP8, as well as new design and usability improvements:

- **Instantly effective** — permission changes are now effective instantly across all branches, including draft and master (published) items, without the need for republishing.

- **Apply to** — Apply permissions to (single item, children only, or both)

- **Overwrite** - intuitive overwrite option for applying permissions, with clear indicators for what will be overwritten and what will be preserved.

- **Summary** — Improved summary section that clearly shows the current permissions and the changes that will be made.

### Pluggable preview

The preview has been redesigned and rebuilt as a pluggable system, allowing for more flexible and customizable previews for different content types and use cases.

- **Bring your own preview** — developers can now create custom preview components for any use-case using the extension system and Enonic apps.

- **Automatic detection** — Content Studio will automatically detect and use the optimal preview for each content item, based on the content type and available preview components.

- **Image editor** is now integrated with media preview, allowing for a more intuitive experience when previewing and editing images.

- **Secure by default** — previews are rendered in a secure sandboxed environment, using browser domain isolation to protect from potential security issues with untrusted content.

### Pluggable page editor

While conceptually similar, the page editor has been completely redesigned to work with any web-based front-end framework, and the new pluggable preview. Highlights are:

- **New component view** — The component tree view has been redesigned for better visibility, interaction and use of real estate

- **Redesigned Visual Editor** — for a cleaner interface with better drag-and-drop support, clearer component hierarchy, and more intuitive workflows.

- **NPM module** — Page editor is now available as a standalone NPM module, allowing developers to integrate it with any 3rd party framework or front-end.

- **Event-based** — for secure communication between Content Studio and the visual editor, enabling cross-iframe drag and drop and other advanced interactions.

### Version history

The version history widget has been updated to take advantage of the new features in XP8.

- **Show only revertable versions** — by default, only versions that can be reverted to are shown in the version history, reducing clutter and confusion for users.

- **Show all actions** — users can choose to show all actions if they want to see the full history of changes and events for a content item.

- **Lazy loading** — version history now loads versions on demand, improving performance for content items with many versions.

- **Improved diff dialog** — the diff dialog now shows only the fields that can be reverted, with clearer indicators for changes and improved layout for better readability.

- **Patch handling** — Version history widget informs users when a version is a patch, and prevents reverting to versions that may break content due to missing required fields or other issues.

### Modernized technology

The underlying architecture of Content Studio has been modernized and rebuilt, improving performance, maintainability, agility, and extensibility, and enabling new features and improvements moving forward.

- **New tooling** — built on a new architecture with React and TypeScript, improving maintainability and enabling faster development.

- **Improved pluggability** — New Extension system with improved documentation and use of web components for better encapsulation and interoperability.

- **Improved performance** — faster load times and improved responsiveness across the application, especially in the page editor and content grid.

### Improvements

- **Import content widget** — import widget is now a native Content Studio feature.

- **Archive with a message** — provide a reason/message when archiving content.

- **New-version notification** — Content Studio notifies when a new version is available.

- **baseUrl support** — support for configuring a base URL for your front-end directly in Content Studio.

- **Scheduled publishing defaults** — "Online from" defaults to "Now", and the Publish button shows a distinct caption for scheduled publishing.

## Known issues

There are some known issues in Content Studio 6.0.0 that we are working to resolve ASAP. These include:

- **Publishing wizard** - Dependencies are not always showing up in the publishing wizard, and the "select all" option is missing for dependencies. This may lead to publishing content with missing dependencies, which can cause issues on the live site.

- **Image editor** — the image editor is now integrated with media preview, but cropping feature is not fully working yet.

- **Image selector** — Drag and drop functionality is not working.

- **Stale data** - for some changes to data the UI does not update immediately, but requires a manual refresh.

- **Fragments** — there are incorrect menu items and preview rendering for fragments.

- **Validation on rename** - The rename dialog does not properly validate the input.

- **Version history** — Some imported content shows wrong dates in version history.

- **Arrow keys** - for some input fields, the arrow keys do not work as expected.

- **Content icons** - it is not currently possible to upload custom icons for content items.

## Upgrade notes

Content Studio 6 requires XP 8.0 or newer, which is a breaking release. In order to start using Content Studio 6 you must

- Upgrade your XP installation

- Upgrade all Enonic apps running on your instance to their latest versions, which are compatible with XP 8.0 and Content Studio 6.0.

Read more about the XP 8.0 upgrade process in the [XP upgrade guide](https://developer.enonic.com/docs/xp/stable/release/upgrade).

**Noteworty:**

- **Xdata is replaced by Mixins** - Only the name changes, the functionality is the same. This is done to better reflect its purpose and use.

- **Rich Text component is deprecated** — and will be removed in a future release. Create your own rich text part and migrate at will. Existing components will continue to work, but insert is now disabled by default.

> **Tip:** Full functionalilty may be re-activated via the [content studio configuration](docs/content-studio/stable/config.md)

- **New URL pattern** — Content Studio is now served without the `/tool/` prefix
