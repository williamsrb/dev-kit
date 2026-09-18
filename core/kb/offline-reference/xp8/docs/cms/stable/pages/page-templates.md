<!-- src:https://developer.enonic.com/docs/cms/stable/pages/page-templates generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/pages/page-templates.md

# Pages templates

Reuse the same page across multiple content items.

## Introduction

Page template is a built-in content type in Enonic XP, and similar to [pages](docs/cms/stable/pages.md), they are only available in the context of a site.

Page templates may act as a starting point when creating new custom pages. Additionally, you may also allow editors to control the presentation of other structured content types like Articles.

## Usage

Editors work with, edit and publish page templates like any other content. Naturally, the main focus on a page template is setting up a page. Like for any other page, at least one [page component](docs/cms/stable/pages.md) must be available in order to actually create a page template.

In addition to creating the page itself, editors may flag which content types the page template applies to. By specifying `Article` as the supported content type, the page template will be reused for rendering of all articles in the site.

The idea is not that editors may control the details of how the article itself is presented, but rather the surrounding compoents and layout of the page where the article is presented. Developers should provide specific components for rendering the actual article, and the editors may then place this component centrally within their page template.

> **Note:** A single `Article` may also be configured with a custom page, or it may be flagged to use a specific page template. If so, this will override the page template defined above.

## Rendering

Page templates should be resolved and rendered by your front-end according to the following rules (in order of precedence):

- If a page is customized, render the page itself (ignore any page templates)

- If a page template is specified explicitly on the content item, use that page template.

- Else, if a page template exists matching the specified content type, render using that page template.

> **Tip:** Also, check out our [Next.js integration](https://developer.enonic.com/docs/next.xp), where page templates are supported out-of-the-box.

### Definition (portal:page-template)

The page template content type is built-in. It is a subtype of `base:structured`, and has the following definition:

super-type

base:structured

is-abstract

false

is-final

true

allow-child-content

true

### Template folder (portal:template-folder)

Every site automatically creates a child content of this type named _templates, using the built-in type `portal:template-folder`. The templates folder contains all the page templates for the site. It may not hold any other content type, and it may not be created manually in any other location.

super-type

base:folder

is-abstract

false

is-final

true

allow-child-content

portal:page-template
