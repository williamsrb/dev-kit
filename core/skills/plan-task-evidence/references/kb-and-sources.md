## Two doc sources (do not mix roles)

| Source | Path | Role | Write back? |
|--------|------|------|-------------|
| **Testing KB** | `~/.agents/kb/testing` | Project/site **instrumentation** — click paths, selectors, auth tips, Guillotine/Data Toolbox queries | **Yes** (during plan *execution*, not this skill) |
| **Offline reference** | `~/.agents/kb/offline-reference` | Official **LLM-dense** product/API docs (Content Studio, XP, React4XP, …) | **No** — refresh via sync scripts only |

Prefer testing How-Tos for *how we automate this site*. Prefer offline-reference when the
flow depends on *how Content Studio / XP / React4XP actually works* (create content, publish
wizard, layers, page editor, rich text, permissions, lib APIs) and the How-To is missing or
thin. Catalog index: `~/.agents/kb/offline-reference/README.md`.

## Knowledge base — purpose and self-feed loop

The KB at `~/.agents/kb/testing` is **not** an evidence dump. It stores **how to perform
tasks** (instrumentation): UI steps, selectors, CMS navigation, auth realms, URL
patterns, and Guillotine/Data Toolbox queries — so agents can run tests **by themselves** on
the next issue.

| Store in KB | Do **not** store in KB |
|-------------|------------------------|
| Repeatable procedure (ordered steps) | Full screenshot sets, Jira comment text |
| Stable selectors, field names, save/publish sequence | Large booking dumps, email bodies, audit tables |
| Minimal **sample data** (one example email, one tour slug, one date) | Every test run's IDs unless they illustrate a reusable pattern |
| Auth tips, blockers, "needs referer" notes | Task-specific acceptance-criteria prose |

**Folder layout:**

| Path | Content |
|------|---------|
| `~/.agents/kb/testing/_shared` | Cross-project instrumentation (e.g. Enonic Content Studio, Guillotine, Data Toolbox) |
| `~/.agents/kb/testing/<project>` | Project-specific flows (`as` for Authentic Scandinavia) |

**File naming:** `How-to-<verb>-<object>.md` (e.g. `How-to-search-components-via-guillotine.md`,
`How-to-start-booking-from-tour.md`). Link related guides; split when a file grows
past one concern.

**Sample data rule:** one short **Sample data** section at the end — only values
needed to execute the procedure (e.g. review base URL, one bookable tour slug, one
test email). Never the focus of the document.

See [kb-format.md](kb-format.md) for the How-To template. KB write-back instructions
belong in the plan file’s **Execution** section (filled from [templates.md](templates.md)).
