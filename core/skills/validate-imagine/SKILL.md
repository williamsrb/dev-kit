---
name: validate-imagine
description: "Validate an imagine context lake against the original concept and fix deviations, contradictions and incomplete work in place. Not for creating a lake (imagine), generating assets (imagine-design), plan review (validate-plan) or delivery QA (validate-impl)."
argument-hint: "<lake path> [--concept <text|file>] [--report-only]"
metadata:
  recommendedRole: impl-review
  reviewOf: imagine, imagine-design
  aliases: imagine-validate, validate-lake, review-lake
  cliDependencies:
    required: [python3, rg]
    optional: [agentctl, magick, ffprobe]
---

# Validate Imagine

Validates **and fixes** an `imagine` context lake. The lake on disk is the contract; a chat-only review is not success. Same stance as `validate-plan` and `validate-impl`: find, fix toward the source of truth, re-check, report, stop.

Run it in a fresh session on a different model than the one that ran `imagine`. It spawns nothing, runs no expansion wave and generates no asset.

## Not this skill

| Need | Use |
|---|---|
| Build a lake from a brief | `imagine` |
| Generate or redo assets | `imagine-design` |
| Review an implementation plan | `validate-plan` |
| Review code against a plan | `validate-impl` |

## Authority: what "the original concept" is

Highest first. A lower layer never overrides a higher one; every fix moves a lower layer toward a higher one.

| # | Layer | Where |
|---|---|---|
| 1 | The operator's words in this chat (corrections, exclusions) | chat. Beats everything (`How-to-respect-user-scope-exclusions.md`) |
| 2 | The original brief, verbatim | `brief.md` "Original brief", or `--concept`. Older lakes: the one-line brief in `README.md`; say the baseline is weak |
| 3 | Settled decisions from P0 | `brief.md` |
| 4 | Canon | `canon.json`: derived from 1-3, changed only in P3 or by a logged P8 decision |
| 5 | Art direction | `design.json`: derived from canon and research |
| 6 | Everything else | persona, research, steps, risks, registry, story, plan, findings, README, assets |

Layers 1-3 are never edited. A decision `run-log.md` already adjudicated (a rejected deviation, an accepted proposal) is not re-raised unless it contradicts layers 1-3.

## Defect classes

| Class | Meaning |
|---|---|
| **Deviation** | The output departs from the concept: contradicts or ignores a stated point (audience, medium, era, tone, scope, exclusion), adds scope the brief never asked for, or silently narrows it |
| **Contradiction** | Two statements in the lake cannot both hold (story vs registry, canon vs design, counts, dates, names) |
| **Incomplete** | A required thing is absent or hollow (template section, step with no actor or case, character with no story role, pending asset, unmarked claim, unlogged drop) |

Checklists, detection and default fixes per class: [references/checks.md](references/checks.md). Report and log formats: [references/report.md](references/report.md).

## Modes

| Mode | Trigger | Behavior |
|---|---|---|
| **fix** (default) | `validate-imagine`, `validate-lake` | Full pass, fix, re-validate |
| **report** | `--report-only`, `review-lake` | Same pass, edits nothing; writes only `validation-log.md` |

## Commands

```bash
V="python3 $HOME/.agents/skills/validate-imagine/scripts/lake_audit.py"
R="python3 $HOME/.agents/skills/imagine/scripts/registry.py"
A="python3 $HOME/.agents/skills/imagine-design/scripts/assets.py"
$V snapshot --dir <lake>            # undo copy in <lake>/.validation/<run-id>/before/
$V audit --json --dir <lake>        # exit 1 on blocker or major
$R check --json --dir <lake>        # included in audit
$R render --dir <lake>
```

`audit` runs the registry check and covers files, template sections, claim counts, access dates, README counts, `[[id]]` use, unused characters and places, design and manifest agreement, unlogged expansion drops, and word candidates for forbidden or above-ceiling things (`review` severity: judge each, do not trust it).

## Context budget

Read in full: `brief.md`, `canon.json`, `design.json`, `README.md`, `run-log.md`, `story.md` (the consistency spine). Registry through `registry.md` or one line per entity. Other prose through `agentctl markdown slice` on the headings a check names. `research.md` and `sources.md` only for claim checks. `expansions/*.md` only when a finding points there. Assets through `manifest.json` and `assets/sheets/`.

## Workflow

```text
- [ ] Resolve the lake and the baseline
- [ ] Snapshot (fix mode)
- [ ] Mechanical audit
- [ ] Deviation pass
- [ ] Contradiction pass
- [ ] Incompleteness pass
- [ ] Asset pass (when assets/ exists)
- [ ] Fix (fix mode)
- [ ] Re-validate (one extra round at most)
- [ ] Write validation-log.md, refresh README and registry.md
- [ ] Report and stop
```

1. **Resolve.** Lake = the argument, else the current directory when it holds `registry.json`, else the newest folder under `~/.agents/imagine/`; state which. Read the baseline files. Write the concept as at most 3 sentences, then a **concept trace table**: one row per atom of layers 1-3 (each named audience, platform, era, tone, setting, mechanic, constraint, exclusion). Columns filled later: where honored, deviated, or absent.
2. **Snapshot.** `$V snapshot`. The lake is not in git, so this is the only undo.
3. **Audit.** `$V audit --json`. Triage: blocker and major get fixed; `review` candidates get judged (real finding, or dismissed with a reason); minor gets fixed when cheap.
4. **Deviation pass.** Walk the trace table through canon, design, story, steps, plan, findings in that order. Every row ends honored, deviated or absent. Then scan the other way: what does the output contain that no atom licenses (scope creep)?
5. **Contradiction pass.** Build the fact table from story and registry, then compare it against steps, plan, findings and design (kinds listed in `references/checks.md`). `rg` every name and number you are about to rule on.
6. **Incompleteness pass.** `references/checks.md`, per artifact.
7. **Asset pass.** Read-only: `$A check --json` on listed files when `magick` exists, then the contact sheets in `assets/sheets/` against the checklist in `~/.agents/skills/imagine-design/references/consistency.md`. Output is the redo list. Audio, video and 3D you cannot review are reported as not reviewed.
8. **Source spot-check** (optional, fix mode or report). Open at most 5 load-bearing verified sources. A 404, or a page that does not support the claim, turns the claim into `(unverified)` and fixes the counts. An unreachable page changes nothing. Never invent or "repair" a URL.
9. **Fix.** Fix policy below. Log every edit.
10. **Re-validate.** `$V audit`, `$R check`, re-read each edited section, re-sweep the trace table rows the fixes touched. One more fix round if blockers or majors remain; then stop and report what is left.
11. **Write** `validation-log.md` (append a run section), update the README file table, recompute README and findings counts, `$R render`.
12. **Report** in chat per `references/report.md`. Stop. Do not run `imagine`, `imagine-design`, `develop-*` or anything downstream from here.

## Fix policy

- **Direction.** Deviation: rewrite or narrow the derived artifact; never widen the concept toward the output. Contradiction: keep the statement from the higher layer; same layer, keep the one most other artifacts corroborate; still tied, keep the one closest to the brief's wording and record it as an assumption. Fix every site (`rg` the stale value): one root cause, fixed once, everywhere.
- **Entities.** As in `imagine`: fix when the entity's role in the story survives the change; reject when the deviation is the point of the entity. Reject by deleting it from `registry.json`, then `$R check` for the links it leaves dangling. Never rename an id except to resolve a duplicate.
- **Incomplete.** Fill from material already in the lake (brief, research, canon, registry), in the persona's voice, inside the canon. A gap that needs new entities: write a result JSON, `$R merge --origin V<n>`, `$R check`; one entity per named gap, no more. A gap that needs a new region, subsystem or expansion wave stays `open`: name it, tell the operator to rerun `imagine`.
- **Canon.** Edit `canon.json` only when it contradicts layers 1-3 (fix toward them) and log why; never to bless an output deviation. After a canon change, rerun `check` and re-sweep what depends on the changed axis.
- **Design.** Edit `design.json` only to resolve a contradiction with canon or brief, or to fill a required direction value the canon or research implies. A value only taste can pick becomes a proposal in the report. Any changed design value adds every affected asset to the redo list.
- **Assets.** Never generate, edit, rename or delete under `assets/`, and never touch `manifest.json`. Deviating, failed and pending assets go on the redo list.
- **Sources.** Never invent a source, URL, date or figure. A claim without a verifiable source is marked `(unverified)` and counted so.
- **Ambiguity in layers 1-3** (the brief contradicts itself, or is silent on a point the output decided and the choice changes the concept). Operator present: ask once with 2-3 options, recommended first. Unattended, or a minor point: pick the reading that satisfies the more specific statement, add it to `canon.json` `assumptions` and findings "Open assumptions", log it.
- **Never**: delete a lake file, edit layers 1-3, run git, regenerate prose that has no finding against it, or rewrite voice and style beyond a finding.

## Severity and verdict

| Severity | Examples |
|---|---|
| **Blocker** | Deviation from audience, medium, era, tone, scope or an exclusion; canon axis violation; contradiction in a fact the story or plan depends on; missing core file; no story root |
| **Major** | Other contradictions; missing or empty template section; unmarked claim; character or place with no story role; wrong counts; failed, pending or deviating asset |
| **Minor** | Convention slips (`[[id]]` outside story and steps, section order), unlisted assumption |
| **Review** | Mechanical candidate awaiting your judgment; resolve to one of the above or dismiss with a reason |

| Verdict | Meaning |
|---|---|
| **PASS** | Nothing found beyond Minor |
| **PASS WITH FIXES** | Every Blocker and Major was fixed; what remains is asset redo or a pending provider key, or Minor |
| **FAIL** | A Blocker remains, or a Major that needs an expansion wave or an operator decision |

## Final reply: next step (always last)

PASS or PASS WITH FIXES with a non-empty redo list, put this block right after the 👉 line, as the last thing in the reply, with the lake path and ids expanded. Skip it when `called_from` is set or `AGENTCTL_FACTORY` is set. No redo list or FAIL: no block; the 👉 line names the decision or the rerun.

```text
/imagine-design <lake path>/design.json --assets <id,id,...>
```
