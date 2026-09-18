<!-- src:https://developer.enonic.com/docs/content-studio/stable/projects/layers generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/projects/layers.md

# Layers and localization

Content Studio offers an advanced concept for localization called Layering

## Concept

Layers are essentially a [Content project](docs/content-studio/stable/projects.md) that inherits content from a different project.

Inherited content can be edited (localized), renamed, re-organized, published or even archived within a single layer. You may also create new content, just like you would in a regular project.

Layers are created and managed just like any other project, but you must specify a parent project, from where it will inherit content.

## How it works

You may have any number of layers, organized in different ways based on your requirements. Here are some examples

Nested layers

Project **A** has a child project **B** which has a child project **C** (and so on).

Siblings

You may have multiple children, so both **B** and **B'** inherit from project **A**.

## Inheritance model

Changes to content in a parent layer automatically propagate to child layers unless the item has been localized in the specific layer.

Example from the above structure:

Content in project **A** will be automatically propagated to **B**, and from there to **C**. If **B** gets localized, it will no longer receive updates from **A**. The modified content from **B** will, however, still trickle down to **C**.

## Listing view

Inherited content in the navigator list will appear as dimmed, providing a visual difference from content that has been localized or created directly in this layer.

Also, all inherited items will have a small blue cloud icon next to it — regardless of whether it has been localized or not.

Sample structure with a single local item

Here the "Search" item is localized to "Søk". The content name has also been localized to "sok".

> **Tip:** Language shown in brackets after the content’s display name means shows that the language of this content is different from the language of the current layer.

## Inheritance types

To make the inheritance flexible, there are four different kinds of inhertance:

- data (your content)

- sorting (of child items)

- parent (location in tree structure)

- and name (name in tree)

An example of how this works is that you can move a content to a different location in the tree (change parent), but its *data*, *name* and *sorting* will still be inherited from the parent

## Localizing

To localize an inherited item, select it and click **Localize**.

> **Note:** For inherited items **Edit** is replaced with **Localize**

This should open the Content Editor. You may now edit and publish the item as if it was created locally. This process effectively terminates further inheritance from the parent item.

## AI translation

> **Note:** **Content Studio+ feature.** AI translation is part of the [Content Studio+](https://market.enonic.com/vendors/enonic/content-studio-plus) subscription. It also requires the [Juke AI Content Translator](https://market.enonic.com/vendors/enonic/juke-ai-content-translator) application.

With the Juke AI translator enabled, clicking **Localize** will instantly reveal the translation dialog. Here you may optionally provide detailed instructions or simply hit **Translate**. This will automatically translate all text fields within your content - just watch it go.

### General instructions

Often, it can be useful to provide standard translation instructions for your content. By adding the application to your project or site, you may configure standard translation instructions that will be used throughout the scope of your content.

> **Note:** Changing these settings requires the [Owner](docs/content-studio/stable/projects.md#project-roles) project role or higher.

## Reset

You may reset a localized item by clicking **Reset** from within the content editor. This will effectively return the item to its original inherited state.

## Layers Panel

> **Note:** **Content Studio+ feature.** The Layers widget is part of the [Content Studio+](https://market.enonic.com/vendors/enonic/content-studio-plus) subscription.

The Layers widget enables the user to see the status of a specific content item in all existing layers in the system.

The current layer is highlighted with a blue border. You can also see how many parents (*Ascendants*) and children (*Descendants*) the current item has.

By clicking an item, a related action button will appear.

Boxes of parent layers where the content item is not localized are hidden by default and can be displayed by clicking on the Ascendants link.

> **Tip:** You can localize content in the current layer directly from the widget.

**Show all** button at the bottom of the widget displays the total number of layers where this item exists. This number can be different from tbe number of boxes displayed in the widget, since the widget only displays the branch of the current layer. To see status of the content item in the entire tree of layers click the button to open the modal dialog.

Just like with the Layers widget, you can expand layer boxes in this dialog to either localize or edit the content in the current layer, or open it in other layers (given your user has sufficient permissions to access the layer).

> **Tip:** Read about the high-level concept of Content Layers [here](https://developer.enonic.com/docs/cms/stable/content/layering).

## Management
