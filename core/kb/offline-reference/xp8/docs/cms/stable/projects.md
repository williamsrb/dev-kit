<!-- src:https://developer.enonic.com/docs/cms/stable/projects generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/projects.md

# Content projects

Independent repositories that provide strict isolation of content, allowing for different access modes and configurations.

## Introduction

Content projects represent the starting point of working with Enonic CMS. In order to create content, you first need to create a project. Project defines if your content is public or private, and what type of content may be produced there. This means, that editors of a particular project will not be able to see, use or link to content within other projects.

## Branches

Each project has two branches where content may exist. The `draft` branch, where all editorial activity occurs, and the `master` branch which is where the published content resides. When content is published, it is replicated from the `draft` branch to the `master` branch. This means that the `draft` branch may contain unpublished changes, while the `master` branch always contains the latest published version of the content.

## General settings

- Identifier - a unique id within the installation. Cannot be changed when first created

- Display name - a human readable name

- Default language - Specifies the default language for content created in the project

## Access mode

Project access mode defines default read permissions for it’s content. The available values are:

- Public (Everyone can read the content)

- Private (only users with project roles can read the content)

- Custom (a specific list of principals can be granted access to read the content, i.e. Employees)

To handle private and custom mode, a special "viewer" role is created and given read access to the content items.

## Roles

To provide access to a project or manage it, users can be granted special roles. The following roles are available per project:

- Contributor - Access to project and issues (must be given specific permissions to create or manage any content)

- Author - Same as contributor, but can additionally create and update content anywhere in the structure

- Editor - Same as Author, but with full permissions and access to rich-text editor source mode

- Owner - Same as Editor, but can also manage the project settings itself, including assigning other users to roles

In addition, a **Viewer** role is auto-created for projects in [Private or Custom](#access-mode) access mode, and grants read access to the project’s content. It is not a manually-assigned project role.

### Capability matrix

Project roles are CMS-level conveniences — underneath, they grant combinations of the seven [content permissions](docs/cms/stable/content/permissions.md#permission-types). The mapping is:

| Role | READ | CREATE | MODIFY | DELETE | PUBLISH | READ_PERMISSIONS | WRITE_PERMISSIONS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Viewer | ✓ |  |  |  |  |  |  |
| Contributor | ✓ |  |  |  |  |  |  |
| Author | ✓ | ✓ | ✓ | ✓ |  |  |  |
| Editor | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Owner | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### Role principal IDs

For each project, dedicated principal roles are created. The roles are named as follows: `com.enonic.cms.project..`

An example might be `com.enonic.cms.myproject.author`.

## Layering

[Project layering](docs/cms/stable/content/layering.md) is a powerful feature that, where each layer inherits content from the parent layer above. This allows you to create different versions of your content for different purposes, such as translations or content for different markets.

## Features

By assigning and configuring Enonic apps for a projects, their Schemas, Extensions and other functionality will be available within the scope of the project. For example, you might have a project for a blog, where you assign a blogging application that provides content types and components for creating blog posts. Configuration of these applications takes effect immediately, without redeploying the app.

> **Note:** The configuration **values** themselves are not exposed through the GraphQL API by default. Because they may hold secrets (API keys, tokens), they are kept server-side unless an app deliberately exposes selected fields. The same applies to [site configuration](docs/cms/stable/pages/site.md#_site_configuration).

[Layered projects](docs/cms/stable/content/layering.md) automatically inherit application settings from parent layers, unless they are overridden in the child layer. This means that if you assign an application to a parent layer, it will be available in all child layers, unless you explicitly override it in a child layer.
