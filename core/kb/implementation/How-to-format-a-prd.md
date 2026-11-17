---
id: how-to-format-a-prd
when_skills: [write-prd, handoff, download-jira-task, plan-implementation]
inputs: [~/.agents/prds/<TASK-ID>.md]
outputs: [PRD file in the shared format]
stop_if: [rewriting existing PRD files only to reformat them]
read: section
prose: caveman-lite
---

# PRD format standard

One file shape for every PRD under `~/.agents/prds/`. Writers: `download-jira-task` (Jira, `<KEY>.md`), `write-prd` (local, `<slug>.md`; `handoff` PRD format goes through it). Readers slice by H2 with `agentctl markdown slice`. New files follow this; old files stay as they are.

## Header

```markdown
# <WORK-ID> — <title>

**Source:** <jira | write-prd | local handoff>
**WORK-ID:** <KEY or slug>
**Type:** <Jira issue type | Feature | Bug | Report>
**Created:** <date>
<source-specific fields>

---
```

Core four fields first, in that order. Source-specific fields after them:

| Source | Fields, in order |
|--------|------------------|
| `jira` | `Updated`, `Jira` (URL), `Project`, `Status`, `Priority`, `Reporter`, `Assignee` |
| `write-prd`, `local handoff` | `Origin`, then `Severity` (Bug) or `Requested by`, `Due` (Report) |

One `**Label:** value` per line. Unknown value: `not stated`, never blank.

## Sections

H2 order. Each H2 block is closed by `---`. Absent sections are skipped, never left empty, except those marked required.

1. `## Description` _(required)_ — local PRDs add `### Context` (Feature), `### Environment` / `### Steps to reproduce` / `### Expected` / `### Actual` (Bug), `### Questions to answer` / `### Scope` / `### Output` (Report)
2. `## Requirement Changes` _(required)_ — see below
3. `## User Scenarios` — `### US<n> — <title> (Priority: P<n>)`
4. `## Acceptance Criteria` _(required for local)_ — checkboxes; `### US<n>` groups when stories exist
5. `## Requirements` — `**FR-###**: System MUST …`
6. `## Key Entities`
7. `## Success Criteria` — `**SC-###**: …`
8. `## Edge Cases`
9. `## Non-Goals`
10. `## Constraints`
11. `## Method` (Report)
12. `## Open Questions` — `**Q<n>** …` with options and default; `None` when empty
13. `## Evidence`
14. `## Comments (<n>)` _(required)_ — `### Comment <id> — <who> — <YYYY-MM-DD>`; local ids `local-<n>`; `(0)` with `No comments.`
15. `## Attachments (<n>)` _(required for `jira`; local only when the source had files)_ — a `Directory:` line with `~/.agents/prds/<WORK-ID>/attachments`, one bullet per file

Jira exports hold 1, 2, 14, 15 only. Sections 1, 14, 15 copy Jira verbatim; 2 is the one extracted section.

## Requirement Changes

Requirements stated after the original request: in comments (Jira), in later messages of the source thread or merged `local-<n>` comments (`write-prd`), or in the operator's corrections later in the chat (`handoff`). Readers treat it as overriding Description and Acceptance Criteria.

Counts: a comment that adds, removes, or changes scope, behavior, acceptance, constraints, target environment, or deadline; an answer that settles an open question. Does not count: a question with no answer, status or progress notes, thanks, bot or CI noise, a proposal nobody accepted.

```markdown
## Requirement Changes

- **RC1** — Comment <id> — <who> — <YYYY-MM-DD>: <the change, one sentence>. Supersedes: <short quote or section of the original, or "adds">.

Checked through: <id of the last comment reviewed | none>
```

Codes `RC<n>` in comment order. A later change to the same point gets its own entry and names the entry it replaces. Empty: `None detected.` The `Checked through:` line is always the last line of the section.

- `jira`: `render_issue.py` writes `None detected.` when no comment is kept, else the pending line `Not extracted yet.`, and `Checked through: none`; `download-jira-task` Step 3b fills the entries and the marker after every fetch. Description stays verbatim.
- Local: the writer applies the change to the affected AC/FR and records the entry, so the history stays visible.

### Comments from other agents

Other agents (and the operator) may append to a local PRD. They add `### Comment local-<n> — <who> — <YYYY-MM-DD>` under `## Comments`, next free `n`, and touch nothing else. Their comments are not applied until the operator refreshes.

### Refresh and staleness

`python3 ~/.agents/skills/write-prd/scripts/requirement_changes.py <prd> --json` lists the comments after the marker (`unchecked`) and sets `stale`; exit 1 when stale. A missing marker means every comment is unchecked; a PRD with no comments is never stale.

- Refresh is manual: `write-prd` "refresh `<slug>`" for local PRDs, a new `download-jira-task` run for Jira PRDs.
- `plan-implementation` runs the check and stops on a stale PRD, naming the unchecked comments and the refresh command. It never applies comments itself.

## Footer

```markdown
*<Exported from Jira | Written by write-prd | Written by handoff> on <YYYY-MM-DD>*
```

## Text rules

- Product language; no chat markers (emoji, `&nbsp;`), no caveman compression. Local paths and `path:line` go under Evidence or Context.
- Codes `US<n>`, `FR-###`, `SC-###`, `Q<n>`, `RC<n>` numbered in order, never reused.
- Dates `YYYY-MM-DD`. Jira timestamps stay as Jira returns them.
