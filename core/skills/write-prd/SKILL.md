---
name: write-prd
description: "Write a structured local PRD at ~/.agents/prds/<slug>.md from a raw request: a feature request (new behavior), a bug entry (existing behavior to fix), or a report/research request (data extract or research deliverable). Spec-kit style stories, Given/When/Then criteria, FR/SC lists, open questions. Use when asked to write, draft, or author a PRD, spec, or requirements from a request, email, Slack thread, or notes. Not for an existing Jira issue (download-jira-task); handoff calls it for its PRD format."
argument-hint: "Source (text, file, URL) — optional type (feature|bug|report) and slug"
metadata:
  recommendedRole: plan
  aliases: draft-prd, author-prd, prd-from-request
  cliDependencies:
    required: [agentctl, python3]
    optional: [rg]
---

# Write PRD

Turn one raw request into one PRD at `~/.agents/prds/<slug>.md`. Write one file, validate it, stop.

There is never a Jira key here. The PRD is local; the operator may copy it into a new Jira task by hand. This skill never reads from or writes to Jira. A request that names an existing Jira issue is not for this skill: use `download-jira-task`.

Follow `~/.agents/kb/implementation/How-to-resolve-task-context.md` for the slug. Never invent a Jira key. Redact secrets and personal data the deliverable does not need (customer names, emails, phone numbers in pasted mails).

## Step 1 — Classify the source

| Type | Signal | The PRD answers |
|------|--------|-----------------|
| **Feature** | Asks for behavior that does not exist yet, or a change to working behavior | What users can do after delivery, and how we test it |
| **Bug** | Says existing behavior is wrong: error, wrong output, regression, "used to work" | How to reproduce, what correct looks like, how we prove the fix |
| **Report** | Asks for a data extract, export, audit, analysis, or research answer; the deliverable is a document or dataset, not shipped code | Which question, for whom, from which data, in which format |

The operator's stated type wins. A request that mixes types: pick the one that decides acceptance (a report that needs a new export endpoint is a Feature). Still ambiguous: ask once.

## Step 2 — Gather the source

Read only what the request points at:

- Text in chat, a pasted email, Slack thread, or file: use as is. Keep quotes short; summarize long threads.
- This conversation (`called_from: handoff` or `plan-implementation`): the chat is the source. Keep the decisions, constraints, and exclusions as finally stated; drop options that were discarded along the way. The operator's later corrections are requirement changes.
- A project path named in the request: confirm the area exists (`graft ask` / `rg`) so the PRD cites real files, routes, content types. Do not design the fix.
- An extract-kit run for that project (operator names it, or a sidecar exists): the as-is specs live at `<run>/spec-kit/specs/<capability>/spec.md`; pick the capability from `<run>/business/capabilities.json`. Cite matching `FR-###`/`SC-###` as current behavior. Bug: the spec says what "correct" was. Feature: the spec says what must keep working.

Do not read other tasks' PRDs or plans.

## Step 3 — Resolve the slug

1. Slug: operator-supplied kebab → else derived from the title (lowercase, hyphenate, ≤ 6 words) → else ask once.
2. If the slug matches `[A-Z][A-Z0-9]+-\d+` (ignore case), **stop**. That path is a Jira PRD owned by `download-jira-task`.
3. `~/.agents/prds/<slug>.md` exists and the operator did not ask to replace it: update only the sections the new source changes.
4. **Refresh** ("refresh `<slug>`", or the PRD exists and the request brings no new source): run `python3 scripts/requirement_changes.py ~/.agents/prds/<slug>.md --json`. Process only the `unchecked` comments: add their `RC<n>` entries, apply each change to the affected AC/FR, update `## Comments (<n>)` to the real count, and move `Checked through:` to the last comment id. Leave everything else as it is. Nothing unchecked: report "already current" and stop.

## Step 4 — Write

Load [references/templates.md](references/templates.md) and use only the chosen type's template. Rules for every type:

- **Facts from the source only.** Mark anything else in the narrative sections `_(inferred)_` with the reason. Acceptance criteria hold only what the source states: an extra the source did not ask for is not a criterion (`plan-implementation` classifies it as an implicit requirement). One exception: a Bug always gets the template's regression-guard criterion, because a fix that breaks neighboring cases is not a fix. A gap is an Open Question, never an invented criterion.
- **Requirement Changes** are detected, not asked for: any later message in the source (thread reply, merged `local-<n>` comment, the operator's correction in chat) that changes the request. Apply each to the affected AC/FR and log it as `RC<n>` per `~/.agents/kb/implementation/How-to-format-a-prd.md` § Requirement Changes. None: `None detected.` End the section with `Checked through: <last comment id | none>`.
- **Open Questions** carry 2–3 options, recommended first, and the default that applies if nobody answers (`~/.agents/kb/_shared/How-to-write-analyst-questions-with-options.md`). Empty: `None`.
- **Testable wording.** Every acceptance item is Given/When/Then or a measurable check. No "should work well", "fast", "user-friendly" without a number.
- **Behavior, not implementation.** Requirements say what the system does, not which function to edit. File paths go in Context/Evidence as pointers.
- **Review, never production.** Reproduction and acceptance happen on review or local, per `../plan-implementation/SKILL.md` § Environment boundary. A production URL in the source is the reporter's symptom; record it under Evidence and restate the scenario for review.
- **Scope exclusions the operator stated** go to Non-Goals and Constraints verbatim (`~/.agents/rules/claude/13-user-scope-exclusions-beat-inference.md`).
- **Product language.** The operator may paste it into Jira. Plain sentences, no chat markers, no caveman compression; keep local paths and `path:line` under Evidence.
- Follow `~/.agents/kb/implementation/How-to-format-a-prd.md` for header order, section order, and footer. `## Description`, `## Requirement Changes`, `## Acceptance Criteria`, and `## Comments (<n>)` are required; `plan-implementation` slices them.

## Step 5 — Validate and report

1. `agentctl markdown slice <file> --sections description,requirement-changes,acceptance-criteria,open-questions --json`: all four found and non-empty. Then `python3 scripts/requirement_changes.py <file>` exits 0.
2. Self-check: every user story has at least one criterion; every FR is covered by a criterion or SC; no criterion depends on production; every `_(inferred)_` has a reason.
3. Reply with the absolute path, type, counts (stories, criteria, requirement changes, open questions), and the open questions that block planning. Nested `called_from`: confirm only. Standalone: offer `plan-implementation` (Feature, Bug) or running the report (Report).

## Final reply: next step (always last)

Feature or Bug PRD, put this block right after the 👉 line, as the last thing in the reply, with `<TASK-ID>` expanded (Jira key or slug). The operator pastes it into a fresh session. Skip it when `called_from` is set or `AGENTCTL_FACTORY` is set.

```text
/plan-implementation <TASK-ID>
```
