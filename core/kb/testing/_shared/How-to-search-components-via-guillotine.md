---
id: how-to-search-components-via-guillotine
when_skills: []
read: section
prose: caveman-lite
---

# How to search for components via Guillotine (Enonic XP)

## Preference

Use the Content Studio **Guillotine** widget when locating pages that use a
part, layout, or page controller. This is the preferred component-search path
for both XP 7 and XP 8.

Use Data Toolbox only for raw node searches, node/property creation,
permissions, ACL repair, or Data Toolbox service calls. Do not start a
component lookup in Data Toolbox when Guillotine is available.

## Prerequisites

- Logged-in XP admin / Content Studio session.
- The component kind and descriptor to locate, such as a part or layout
  descriptor (`app.name:component-name`).

## URLs

Open the version-specific Content Studio Guillotine widget:

| Version | URL path |
|---|---|
| XP 8 | `/admin/com.enonic.app.contentstudio/main#/english/widget/guillotine/guillotine` |
| XP 7 | `/admin/tool/com.enonic.app.contentstudio/main#/en/widget/guillotine/guillotine` |

Prefix the path with the review or staging host base URL. XP 8 has no `/tool/`
segment; XP 7 uses the classic `/tool/` path.

## Procedure

1. Open the matching Guillotine URL for the XP version.
2. If Content Studio asks for a project, select the project that contains the
   target site (XP 8 commonly uses `english`; XP 7 commonly uses `en`).
3. Use the Guillotine widget's schema/query controls to search the relevant
   component collection (`part`, `layout`, or `page`) by descriptor.
4. Inspect the returned content paths and identify a page that is published in
   the branch required by the test.
5. Open the matching page in Content Studio or its public preview and verify
   the component before using it as test evidence.
6. Map the confirmed content path to the environment's public URL. Do not
   assume the content path's language segment is the public URL language
   segment.

## Pitfalls

- The widget requires the same authenticated admin session as Content Studio.
- XP 8 requests using the XP 7 `/admin/tool/` route return 404; XP 7 requests
  without `/tool/` use the wrong route.
- A component can appear in draft but not on the public site. Confirm the
  branch and publish state before selecting an evidence page.
- If Guillotine is unavailable, use Data Toolbox as a documented fallback and
  record that fallback in the test report.

## Sample data (minimal)

| Field | Example |
|---|---|
| XP 8 path | `/admin/com.enonic.app.contentstudio/main#/english/widget/guillotine/guillotine` |
| XP 7 path | `/admin/tool/com.enonic.app.contentstudio/main#/en/widget/guillotine/guillotine` |
