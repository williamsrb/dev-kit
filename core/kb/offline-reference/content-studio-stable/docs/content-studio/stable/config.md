<!-- src:https://developer.enonic.com/docs/content-studio/stable/config generated:2026-07-29T03:46:58Z format:llm-dense content-studio-stable -->
#DOC docs/content-studio/stable/config.md

# Configuration file

This section describes how to configure Content Studio via the config file.

Add config properties to this file:

```filename
$XP_HOME/config/com.enonic.app.contentstudio.cfg
```

## Enable Rich Text component

```properties
settings.enableTextComponent=true
```

Rich Text component was deprecated in Content Studio 6.0. The setting above will enable it.

## Matching mode for content type patterns

```properties
contentTypePatternMode = MATCH
```

Defines matching mode for content type patterns. Can be `MATCH` or `LEGACY`. Default: `MATCH`. See [description](https://developer.enonic.com/docs/cms/stable/schemas/form-items/contentselector#allowContentType).

## Max file upload size

```properties
uploadMaxFileSize = 100mb
```

Used for setting size limit on attachments, media content and both project and content thumbnail uploads

## Disable path name transliteration

```properties
contentWizard.allowPathTransliteration=false
```

Turn off automatic transliteration of name when generating it based on a value typed into the display name field in the Content form.

## Content Security Policy

Enonic XP and Content Studio enforces several layers of Content Security Policy (CSP) to prevent cross-site scripting, clickjacking and other code injection attacks resulting from execution of malicious content in the trusted web page context.

You may override the default CSP header via the `contentSecurityPolicy.header` property.

### Widgets

Content Studio uses widgets from other applications extensively. As widgets are loaded into Content Studio’s context, they must comply with the Content Studio CSP.

By default, widgets with inline scripts/styles or scripts loaded from external domains will be blocked.

#### Example: Google Analytics Widget

The [Google analytics app](https://market.enonic.com/vendors/enonic/google-analytics) injects its own scripts referring to an external domains. See CSP example in the [GA app documentation](https://developer.enonic.com/docs/google-analytics/stable#content_security_policy).

#### Example: Disable CSP

If you trust all of the widgets you use in Content Studio, you may disable the CSP completely:

```properties
contentSecurityPolicy.enabled=false
```

### Site Engine Preview

Content Studio’s preview uses an iFrame to isolate the client-side assets from interfering with the Content Studio’s own.

In production, front-ends built with the Enonic site engine deployed on custom domains. In preview mode however, the site engine is accessed in the same domain and URL context as Content Studio. To mitigate this, Site Engine has a standard preview CSP to protect Content Studio and the XP admin.

If your site is not working properly in preview mode, consider improving the implementation. Details on tuning the Site Engine CSP are described in the [XP configuration documentation](https://developer.enonic.com/docs/xp/stable/deployment/config#admin).

> **Note:** While using Site Engine in visual edit mode, the CSP is strictly enforced, and is currently not possible to override.

## Publishing Wizard

### Disable "Mark as Ready" action

```properties
publishingWizard.allowContentUpdate = false
```

Whenever the Publishing Wizard contains at least one item that is "*Work in progress*", publishing will be disabled. The editor can solve this by clicking the "**Mark as ready**" link on top of the dialog, which will mark all such items as "*Ready for Publishing*".

To add another level of restriction and prevent accidental publishing of items that are not ready for publishing, the "**Mark as ready**" bulk action can be disabled by adding the parameter above to the config file.

### Default "Online from" time

```properties
publishingWizard.defaultPublishFromTime = 12:00
```

The default value can be changed by setting the `publishingWizard.defaultPublishFromTime` config property.

### Required "Online from"

By default, when scheduling new publishing the "Online from" field will be preset to "Now", which means that the content will go online immediately. It’s possible to make this field mandatory to make sure the user explicitly sets the date/time when the content will go online.

```properties
publishingWizard.requiredPublishFrom = true
```

### Exclude optional dependencies

```properties
publishingWizard.excludeDependencies = false
```

By default, only mandatory dependencies (ascendant items and inbound references) of the content staged for publishing will be automatically loaded and displayed in the list of dependencies in the Publishing Wizard with checkboxes selected and disabled. Optional dependencies (like outbound references) will be loaded as well, but they will **not** be preselected and can be added to the publishing batch manually by the user.

It’s possible to overrule this behavior and preselect all the dependencies – both mandatory and optional – by setting the `publishingWizard.excludeDependencies` config property to `false`. This will ensure that the content will be published with no broken references.

Figure 1. Only mandatory dependencies (default behaviour)

Figure 2. All dependencies
