---
id: how-to-search-via-datatoolbox
when_skills: []
read: section
prose: caveman-lite
---

# How to use Data Toolbox for node and ACL operations (Enonic XP)

> Component lookup has moved to the Content Studio Guillotine widget. Use the
> [Guillotine How-To](./How-to-search-components-via-guillotine.md) for parts,
> layouts, and page controllers. Keep this guide for raw node searches, node
> and property operations, permissions, and Data Toolbox services.

## Prerequisites

- Logged-in XP admin session (`/admin`)
- Tool URL:
  - XP 7 / classic: `<base>/admin/tool/systems.rcd.enonic.datatoolbox/data-toolbox`
  - XP 8: `<base>/admin/systems.rcd.enonic.datatoolbox/data-toolbox` (**no** `/tool/` — classic path 404s)

## Procedure

1. Open **Node Search** in Data Toolbox.
2. Leave repositories/branches as needed (often “All”).
3. Put a NoQL query for raw node fields in the **Query** field.
4. Click **Search** and read result rows (`name`, `repo:branch:path`, score).
5. Map a content `_path` to a public site URL only after confirming the
   repository, branch, and site language.
6. Prefer **master** hits for live evidence; skip `_templates` and archive
   unless testing those.

## Component lookup

Do not use old Data Toolbox component queries from existing plans. Open the
[Guillotine component-search guide](./How-to-search-components-via-guillotine.md)
instead.

## Pitfalls

- Hash-route search needs an authenticated admin session; unauthenticated opens login.
- Draft vs master duplicates appear as separate hits — use master for public evidence.
- English public paths are not always the same as content `_path` segments (e.g. `dyr` vs `animals`).

## Sample data (minimal)

| Field | Example |
|---|---|
| Base URL (vet NO) | `https://review.vet.k8s.example.com` |
| Base URL (vet EN) | `https://review.vet.k8s.example.com/en/` |
