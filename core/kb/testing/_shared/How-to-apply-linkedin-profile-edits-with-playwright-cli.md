---
id: how-to-apply-linkedin-profile-edits-with-playwright-cli
when_skills: [run-plan, playwright-cli]
inputs: [ranked storage-state JSON, vanity slug, GO’d copy per section]
outputs: [live field matching the GO’d copy]
stop_if: [no section GO, login page after state-load, live re-read diverges from GO]
read: section
prose: caveman-lite
---

# How to apply LinkedIn profile edits with Playwright CLI

**Scope:** `_shared`
**Applies to:** logged-in `www.linkedin.com` via Playwright CLI (not Voyager writes)
**Related:** `find-auth-storage.py` in plan-task-evidence scripts

## Prerequisites

- Storage state ranked by host, not filename: `python3 ~/.agents/skills/plan-task-evidence/scripts/find-auth-storage.py --json --host www.linkedin.com`
- Named CLI session: `playwright-cli -s=<slug> open` then `state-load ~/.agents/.auth/<ranked-file>.json` then `goto` the profile URL
- Never copy `li_at`, `JSESSIONID`, or session JSON into the plan, git, or chat
- Backup live fields to `~/.agents/prds/<TASK-ID>/backup-<date>-pre-apply/` before the first write (headline, About, experience, skills list, Featured, banner, photo). Keep `/tmp/li-review` dumps out of git
- An explicit operator GO for each section. Un-GO’d fields stay as live

## Procedure

### Auth and session

1. Rank storage with `find-auth-storage.py --host www.linkedin.com`.
2. Open a named session with no profile URL: `playwright-cli -s=<slug> open`.
3. `playwright-cli -s=<slug> state-load ~/.agents/.auth/<ranked-file>.json`.
4. `playwright-cli -s=<slug> goto https://www.linkedin.com/in/<vanity>/`. If the page is login, the state is expired: stop; do not treat the login page as evidence.

### Edit URL patterns (self-view)

Write a field only after GO for that section.

- Intro (headline, name, locale): `/in/<vanity>/edit/intro/`
- About EN: `/in/<vanity>/edit/forms/summary/new/` (no `language=` query)
- About PT: `/in/<vanity>/edit/forms/summary/new/?language=pt&country=BR`
- Experience: `/in/<vanity>/details/experience/edit/forms/<id>/` (`<id>` is the `Edit` link href on `/details/experience/`)
- Skills list: `/in/<vanity>/details/skills/`
- Add skill: `/in/<vanity>/skills/edit/forms/new/`
- Edit one skill: `/in/<vanity>/details/skills/edit/forms/<id>/`
- Reorder / pin order: `/in/<vanity>/details/skills/reorder/`
- Featured details: `/in/<vanity>/details/featured/` then `Edit <title>`
- Cover: profile `Edit background image` → `Edit cover image` → `Change photo`

Write through these forms. Do not invent Voyager POST URLs.

### About

LinkedIn stores paragraph breaks as `<br><br>`. The a11y snapshot concatenates paragraphs into one string. Re-read from `innerHTML` / the textarea value, not from the snapshot text, before declaring a mismatch.

### Skills

1. The All-tab Edit-link list is the **displayed** set (often 20). LinkedIn also keeps a longer inferred list (reorder dialog, category tabs). Count the All-tab Edit links for the 20-skill contract.
2. Saving experience or deleting a skill can auto-fill empty slots from job text (Linux, C#, Hibernate, JQuery, Web Design, Scrum, `.NET`, PT names). After every skill write, re-list All-tab names and delete extras that are not in the target set, then add the missing target names **immediately**.
3. Typeahead: in `playwright-cli run-code` or `run-code --filename=`, click the **exact** option (`getByRole('option', { name: 'JavaScript', exact: true })` or `[role="listbox"] [role="option"]` with `/^Enonic XP$/`). Do not ArrowDown/Enter. Do not press Escape after a custom fill (it clears the field). `getByRole('option')` also matches the language switcher; prefer the listbox locator.
4. `This skill is already on your profile` can mean the name exists on the **long** list (reorder dialog) but not on the displayed 20. Pick the LinkedIn catalog name instead (`React` → `React.js`, `Enonic` → `Enonic XP`) or attach the skill on the experience form (`Add skill` checkbox) then reorder.
5. Delete one skill at a time: Edit form → `Delete skill` → confirm `Delete`. Do not batch `page.goto` deletes (`net::ERR_ABORTED`).
6. Pin order: `/details/skills/reorder/` sortable handles (`aria-roledescription="sortable"`). Space to lift, ArrowUp/Down, Space to drop. First three All-tab names are the user pin. The `overlay/top-skills-details/` dialog is **endorsement**-based and may stay a different trio.

### Featured resume

`/details/featured/` → `Edit <resume title>` → **Edit media** dialog. Title is the first textbox; description the second. Save. Skip GitHub unless a URL is in the GO.

### Banner (1584×396)

1. Profile → `Edit background image` (the button expands a menu; the first click is not the upload).
2. `Edit cover image` → Cover photo dialog → `Change photo`.
3. **Add a cover image** → `Upload single photo` / `Choose an image`. Playwright CLI intercepts the file chooser: `playwright-cli -s=<slug> upload /abs/path.png`.
4. **Edit image** crop: keep zoom 1 when the file is already 1584×396 → `Save changes`. Wait for `Saved successfully`.

### Post-write re-read

After each save, re-open the same field (or details page) and compare to the GO’d copy. Stop if live text diverges. Restore `?locale=en_US` if a PT URL was used for About.

## Pitfalls

- Do not write a field without a GO for that section.
- `open <linkedin-url>` before `state-load` can paint login; load state first, then `goto`.
- A Save click that stays on `/skills/edit/forms/new` is not a save: read the alert (`already on your profile`) before retrying.
- Uncheck “currently working” by clicking the **label text**, not the wrapper div.
- Do not commit `~/.agents/.auth/`, `/tmp/li-review/`, or session screenshots.
- `playwright-cli run-code` runs in the page function; use `--filename=` for multi-step flows. Prefer `playwright-cli upload` over `waitForEvent('filechooser')` when the CLI owns the chooser.

## Sample data (minimal)

| Field | Example |
| ------- | --------- |
| Host | `www.linkedin.com` |
| Vanity URL | `williams-ramos-barboza` |
| Banner size | `1584×396` PNG |
| Skill reorder | `/in/<vanity>/details/skills/reorder/` |
