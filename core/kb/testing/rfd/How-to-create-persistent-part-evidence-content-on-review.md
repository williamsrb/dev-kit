# How to create persistent part evidence content on review

**Scope:** `rfd`
**Applies to:** review (`https://review.rfd.k8s.example.com`), project `default`

## Procedure

1. Never edit published pages for evidence. Duplicate the page instead: `POST /admin/rest-v2/cs/cms/default/content/content/duplicate` with `{contents:[{contentId, includeChildren:false}]}` (only those two fields; extra keys return 500). CS names it `<name>-copy`, draft only.
2. Reuse an existing copy before creating `-copy-2` (`bypath?path=/rfd/<name>-copy`).
3. Do not publish or delete the copy. Edit its part config; preview at `/admin/site/preview/default/draft/rfd/<name>-copy`.

## Sample data

| Copy | Id | Used by |
|------|----|---------|
| `/rfd/sorteringsguide-copy` | `7cba2f6c-0b64-4971-8892-ce05956b1503` | RFD-687 (fallback field left empty) |
