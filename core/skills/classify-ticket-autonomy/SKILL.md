---
name: classify-ticket-autonomy
description: "Classify a ticket as Autonomous (ticket to review with no human) or Human-in-the-loop, against a fixed criteria set, and write a machine-readable verdict for the automation pipeline. Use to triage, gate, or pre-screen a Jira key or local PRD before planning. | recommendedRole: quality-gate | aliases: autonomy-verdict, triage-autonomy, hitl-classify."
metadata:
  recommendedRole: quality-gate
  aliases: autonomy-verdict, triage-autonomy, hitl-classify
  cliDependencies:
    required: [python3, agentctl]
    optional: [rg]
---

# Classify ticket autonomy

One verdict per ticket: **Autonomous** (an agent can take it from ticket to deployed-on-review with no human) or **Human-in-the-loop** (some criterion needs a person before review). The pipeline reads the JSON file; the chat summary is for the operator.

This skill classifies only. It does not plan, code, post to Jira, or ask the analyst anything. Hard-stop after the verdict.

## Scope of "Autonomous"

The delivery boundary is **review**, per `../plan-implementation/SKILL.md` § Environment boundary. Anything after review is out of scope for the verdict: analyst acceptance, production publishing, editor follow-ups, release copy sign-off. List those under `review_followups`. They never make a ticket Human-in-the-loop.

**"Review" means the project's shared test delivery**: the review, staging or prototype host for web apps, or a test build or bundle for non-web work. **"Environments we have access to"** means that plus the agent's own machine (Linux workstation, Docker). A ticket that needs Windows or macOS, a physical device or printer, or real hardware is not reproducible there, even if a human developer delivered it.

## Inputs

1. Resolve `<TASK-ID>` per `~/.agents/kb/implementation/How-to-resolve-task-context.md`. Note `mode` (`jira` or `local`).
2. PRD: `~/.agents/prds/<TASK-ID>.md`. If it is missing and `mode` is `jira`, run `download-jira-task` nested (`called_from: classify-ticket-autonomy`). Never fetch live Jira here.
3. Plan, if one exists (`agentctl plan resolve <TASK-ID>`): read `tbd.md` and `plan.md` § Constraints only. **High-confidence decisions** and **Local PO decisions** there are already resolved.
4. Repo checks only where a criterion needs them (a prototype component exists, a saved auth state covers the review host). Do not read the whole codebase.

## Workflow

```
- [ ] Resolve task, mode, PRD (and plan if any)
- [ ] Scan: python3 ~/.agents/skills/classify-ticket-autonomy/scripts/autonomy.py scan <PRD>
- [ ] Judge all 12 criteria (read every cited line; hits are leads, not verdicts)
- [ ] Apply the high-confidence test to every open question before calling it a blocker
- [ ] Write ~/.agents/prds/<TASK-ID>.autonomy.json
- [ ] python3 .../autonomy.py check <json>  (exit 0 required)
- [ ] Chat summary, then stop
```

The scan reads the title, description, ACs, and comments **not** written by the assignee (their own evidence reports are after the fact). It returns line-cited hits per criterion, the type, status, Figma link count, and comment count.

## Criteria

Each criterion is `pass` or `blocker`. **Any blocker makes the verdict Human-in-the-loop.** Every blocker needs evidence (quoted line + `PRD:L<n>` or a file path), the human action that unblocks it, and its owner.

A blocker is a **fact about the ticket**, not a question you could answer yourself. Before marking a question-shaped item as a blocker, run the high-confidence test in `../plan-implementation/references/classify-and-scope.md` § 3f. If the recommended option passes, record it under `auto_resolved` and mark the criterion `pass`. Apply the test strictly: analysts pick the non-recommended option about one time in six. A choice that contradicts the literal wording of the title or an AC is never high confidence, even when it serves the stated goal better (the title says "as the sender", so auto-selecting Reply-To is wrong even if it delivers better). A choice the ticket explicitly delegates ("developer to choose", "either pattern is fine") is not an open decision: record it in `auto_resolved` with source "delegated by ticket". Options the ticket lists **without** delegating or picking one ("ideally X, at minimum Y", "decide with the team", "resolve before build") are an `owner-decision`, even when one option looks better.

| id | Blocker when | Pass when | Examples |
|----|--------------|-----------|-----------------|
| `other-owner` | The AC needs work another person, team, repo or ticket owns and has not delivered: a frontend prototype component that is missing or whose props don't fit, a pending `(Frontend)` sibling ticket, an external library publish, a shared fix another ticket owns. | The needed component or lib already exists and fits (check `react4xp/components/prototype/` or the lib registry), or the gap can be worked around inside our side as delivered. The ticket explicitly says to build against a mock or that it is not blocked (the end-to-end AC becomes a `review_followups` line). A soft ordering ("best done after X") on work the same pipeline delivers goes in `pipeline_preconditions`. A hard "blocked by X" on undelivered work, or an AC that can only be verified on review once a sibling ticket lands, is a blocker. | a part waits on a missing frontend component; two tickets share one player fix; several tickets wait on one sibling ticket |
| `external-access` | Needs something only a human can supply: credentials, API keys, certificates, test users, a vendor-side configuration (SuperOffice, HubSpot, GTM, Cookiebot, IDPorten, SendGrid), hosting or infra access (kubectl, management API, mail relay, app install by Enonic/hosting), or a login with no saved storage state for the review host. | The capability is already in the repo or on review, or `python3 ~/.agents/skills/plan-task-evidence/scripts/find-auth-storage.py --json --host <review host>` returns a matching state. Secret rotation or env config done by hosting is a `review_followups` line when the code change can be verified on review without it. | eID certificates and test users; the client's tag-manager admin; a mail-provider key that exists only in production; a data export that needs basic auth on review |
| `owner-decision` | A product or business decision with no sourceable default: it fails the high-confidence test (business data that doesn't exist, scope-or-close, choice of client CRM/ESP, alternatives that are equally valid on the ticket's terms). | No open decision, or every one passes the high-confidence test (`auto_resolved`). | no source for prices or ratings; build-or-close; how to handle a backlog |
| `unsourceable-content` | The delivery must contain facts or owner-approved wording the agent must not invent, and the ticket does not supply them: legal or policy text, customer-facing email copy, company facts (addresses, subsidiaries, social URLs), prices. | The text is in the ticket, Figma, prototype or existing i18n, or it is ordinary UI copy or a translation the agent can draft (add a `review_followups` line for sign-off). | submitter email copy; a list of subsidiaries; AI-policy text |
| `existing-data` | The change breaks or rewrites existing content or customer data and needs an owner's rule: removing or renaming fields or options that are in use, making a field mandatory on existing items, splitting or remapping legacy values, remediating customer records. | The change is additive or optional, or the ticket states the migration rule and it is mechanical on review. | colour options removed from published blocks; a new mandatory field on existing forms; splitting a legacy value |
| `review-reproducible` | The behaviour cannot be reproduced or verified in any environment we have access to (review, local; never production): the only example lives on production and is not copied, it needs production logs or customer data, a third party only works with production config, the review env is known to be down, or the ticket reports a symptom we cannot trigger from what it gives us. | A review scenario exists or can be created there (duplicate, recreate, seed). Production-phrased ACs are restated on review, so they are not blockers. | only production booking logs show the failure; a form submit that fails only in production; staging is offline |
| `clear-spec` | The ticket's information is too poor to act on: no expected behaviour, a bug without steps, URL, content or example to reproduce it, a vague forwarded report, wording with two readings that lead to opposite outcomes and nothing (AC, Figma, code) that settles it, or an Epic rather than a deliverable. Filling the gap yourself would be guessing, not a high-confidence choice. | ACs or a clear description settle it; conflicts are settled by the ACs (follow the ACs over Figma). | "need more details on how it was tested"; the linked test case is missing; a one-line "it does work on it" report |
| `commercial-gate` | Work may not start yet: an estimate or quote request, a status like Customer pending or Waiting for approval, an explicit "wait with this", or an open budget question. | No such signal. | "please wait"; "wait until approval"; "how much more time" |
| `operator-gate` | A change the ticket does not clearly authorize and that has impact beyond review: auth or permission model, persisted schema or public contract consumed elsewhere, root CI/infra/DNS/vhost with external impact, a new paid service. Money, identity, real inboxes and irreversible data operations have their own criteria below. | Not present, or clearly requested and reversible within the delivery (BASE § 3). | a GitLab licence and permission policy change |
| `real-money-or-identity` | The delivery handles, or reproducing or verifying it needs, real money or personal identity: payments, refunds, deposits, payouts, invoices, a payment gateway, card or bank data, national ID numbers, passports or other identity documents, eID login (BankID, ID-porten, MinID). A sandbox or test mode on review does **not** clear it. It applies when the changed code, or the path to reproduce or verify it, passes through the payment or identity step, including payment emails and amounts. | None of that is touched; a page merely near the payment step, with no change or reproduction path through it, passes. | a double-payment fix in the payment gateway; deposit reminders; eID login |
| `real-inbox` | Reproducing or verifying would send email, SMS or push to recipients the team does not own (clients, customers, end users), send through a client's real mail or SMS account, or read a real client inbox. | Every message during reproduction and verification goes to a sink or to inboxes the team owns (local SMTP catcher, test recipients configured on review). If the ticket does not say how review routes mail and a real recipient appears in the flow (a customer, a client Cc), it is a blocker. | re-sending reminders to real customers; mail through the client's mail server; the client's mail-provider account |
| `irreversible-operation` | Reproducing, running or verifying could delete or corrupt data that cannot be restored: bulk delete or update scripts, migrations or imports over shared data (review content others use, CMS repos), deleting or unpublishing published content, writes into an external system of record (CRM, ERP, booking, ticketing, a municipal intake system). | It runs only on isolated or duplicated data (for example `/site/test/...` duplicates), as a dry run or inside a transaction, or with a backup and restore path the agent can run and has verified. | a relation-removal script; removing options used by published blocks; form submissions into a municipal intake system |

## Which criterion when several fit

- `real-money-or-identity`, `real-inbox` and `irreversible-operation` are **hard stops**. No high-confidence choice, sandbox claim or "clearly requested" wording clears them. Only a human-provided safe path clears them: a test sink, isolated data, a verified restore. Record that path as the blocker's `human_action`. When one applies, it wins over `operator-gate` and `existing-data`.
- Production data or logs needed to **reproduce** → `review-reproducible`.
- A customer- or vendor-held tool or account (Search Console, GTM, a vendor admin) → `external-access`.
- Unverifiable because a sibling ticket has not landed → `other-owner`.
- A production-only **check** after delivery → `review_followups`, not a blocker.
- The ticket contradicts a project rule that says to ask (for example the repo `AGENTS.md` "When an issue conflicts with these rules") → `owner-decision`, owner `operator`.
- The deliverable **is** infrastructure (a new repo, CI pipeline, K8s namespace, DNS) → `external-access`, owner `hosting`, unless the agent's own rights are known to cover it.
- One cause can fail several criteria (a missing test customer: `review-reproducible`, `external-access`, `real-money-or-identity`). Record every one that applies; each gets its own `blockers[]` entry.

## Not criteria (do not flag)

These look like blockers but are not ticket properties. Recording them as blockers makes the verdict useless.

- **Weak TBD.** Anything that passes the high-confidence test goes in `auto_resolved`. Many plan TBDs are of this kind.
- **Production follow-ups.** Production publishing, editor actions on the live site, production checks. These go in `review_followups`.
- **Review-side CMS setup.** Page templates, site config and test content on review are the agent's job (`~/.agents/kb/testing/_shared/How-to-use-content-studio-xp8.md`).
- **Git merge or push to the review branch.** Pipeline authority, not a ticket property. Report it only in `pipeline_preconditions` when relevant.
- **Agent-behaviour corrections** from past sessions (wrong base branch, unasked Jira posts, ignored saved auth). Those are skill fixes.
- **Rework risk after review.** Figma pixel deltas, empty optional fields, scope added during review. Record it as `risk_flags`, not a blocker.

## Mode

- **jira:** as above.
- **Hard stops apply in both modes.**
- **local:** the planner is the product owner. `owner-decision` and `unsourceable-content` pass through Local PO auto-select unless the missing item is a real-world fact or legal text. The other criteria apply unchanged.

## Output contract

Write `~/.agents/prds/<TASK-ID>.autonomy.json`, then run `autonomy.py check` on it (it enforces the rules below). Re-running the skill overwrites the file. Re-classify after a human supplies a blocker's input.

```json
{
  "task_id": "PROJ-123",
  "mode": "jira",
  "verdict": "Human-in-the-loop",
  "classified_at": "2026-09-23T20:10:00Z",
  "sources": ["~/.agents/prds/PROJ-123.md", "~/.agents/plans/PROJ-123/tbd.md"],
  "criteria": {
    "other-owner": {"result": "pass", "evidence": "backend-only listener; no prototype dependency"},
    "external-access": {"result": "blocker", "evidence": "Scenario C export needs su basic auth on review (plan S4)", "source": "plan implementation.md S4"},
    "...": {"result": "pass"}
  },
  "blockers": [
    {"criterion": "external-access", "evidence": "…", "human_action": "Operator runs the export/import or grants management API access", "owner": "operator", "pre_resolvable": true}
  ],
  "auto_resolved": [
    {"decision": "Auto-publish Base changes into non-localized layers", "chosen": "(a) yes", "source": "PRD Requirement 2, ACs 2-5", "why_alternatives_lose": "per-layer publishing reopens the bug on every Base edit"}
  ],
  "risk_flags": [],
  "review_followups": ["Editors publish existing affected pages on the live site"],
  "pipeline_preconditions": ["Merge/push to review branch"]
}
```

- `criteria` holds exactly the 12 ids above. `verdict` is Human-in-the-loop if and only if some criterion is `blocker`, and `blockers[]` lists exactly those criteria.
- `owner`: one of `analyst`, `client`, `frontend`, `other-team`, `tech-lead`, `vendor`, `hosting`, `operator`.
- `pre_resolvable: true` means the pipeline can request the input up front (a login, a copy of content into review, credentials) and re-classify. `false` means a person has to decide or build something.
- Never copy a secret value into the file or chat. Some PRDs carry plaintext keys and passwords in comments. Cite the line number only.

## Chat summary

```markdown
**<TASK-ID>: Autonomous | Human-in-the-loop**
- Blockers: <criterion: human action (owner)> — or "none"
- Auto-resolved: <n> (<one-line list>)
- Risk flags / review follow-ups: <short>
- File: ~/.agents/prds/<TASK-ID>.autonomy.json (check: valid)
```

Several keys: one line per key, then counts per verdict.
