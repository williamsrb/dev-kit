<!-- src:https://developer.enonic.com/docs/content-studio/5.x/editor/content-form generated:2026-07-29T03:47:31Z format:llm-dense content-studio-5.x -->
#DOC docs/content-studio/5.x/editor/content-form.md

# Content Form

This form appears on the left side of the page after a content is created or while being edited. The structure and fields in the form are determined by the [content type](docs/content-studio/5.x/content-types.md) the content is using. The content form can be collapsed - to give the page editor (on the right) more screen estate - by clicking the icon in the form toolbar.

## Header

The form header contains the content type icon, the Display Name field, and the content path name. The default content type icon can be replaced with a more content-specific thumbnail by clicking on it and uploading an image file. When the Display Name is being changed, the path name will change accordingly, to a URL-friendly version. It is also possible for the Display Name to be generated dynamically using values from other form fields by using a [Display Name expression](docs/content-studio/5.x/content-types.md#display_name_expression).

> **Note:** Value of the Path field must be unique and will be validated against existing content every time the field is changed.

> **Tip:** For a new content, Path will be auto-generated as you type into the Display Name field. International letters will be automatically transliterated into their english equivalents. It’s possible to turn off this behaviour in the Content Studio’s [config file](docs/content-studio/5.x/config.md#content_path_transliteration).

After a content has been published, the Path field gets locked and user must click the path to rename content in the dedicated modal dialog. These precautions aim to prevent accidental breaking of external hard-coded links.

## Form

Under the header is the toolbar with clickable navigation steps that correspond to different sections of the content form. The first one is always the content type name followed by optional **X-data** steps (if any). Clicking on an item in the toolbar will scroll the content form down to the corresponding section.

Clicking the icon in the menu toolbar will collapse the Content Form and give room to the Visual Editor panel.

## Page Components tree

When the content is using a controller, the toolbar menu will contain a step called "Page". This form step contains a hierarchical tree structure of all the components and regions on the page, including the page itself. This tree makes it very easy to manage content structure without having to use the Visual Editor.

Selecting a component in the tree will highlight the component in the Page Editor and display its configuration in the [Page](docs/content-studio/5.x/widgets.md#page) widget. The icon on the right of each component will open a context menu - same as the one that would open for the same component in the [Visual Editor](docs/content-studio/5.x/editor/page-editor.md#editing-page).

Components can be rearranged directly in the tree with drag’n’drop function.

In the image below, a part called **Latest comments** is selected in the Page Components view and highlighted with a blue border/mask in the Page Editor. The selected part’s configuration form is displayed in the Page widget on the right.

> **Note:** For fragments and page templates the Page Components tree will be displayed on top of the form, inside the first step.
