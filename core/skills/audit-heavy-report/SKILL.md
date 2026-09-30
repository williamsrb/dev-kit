---
name: audit-heavy-report
description: "Audit a codebase for five security categories (tenant isolation, UI-only auth, IDOR, hardcoded secrets, XSS) and write a PDF report plus copy-paste GitHub issues. Use on security-audit, pentest-five, or audit-report requests — not delivery QA. | recommendedRole: quality-gate | aliases: security-audit-report, five-flaw-audit, pentest-five."
disable-model-invocation: true
metadata:
  recommendedRole: quality-gate
  aliases: security-audit-report, five-flaw-audit, pentest-five
  cliDependencies:
    required: [git, rg, python3]
    optional: [gitleaks, agentctl]
---

# Audit Heavy Report

Five-category security audit of **real code**, then a PDF report under the audited repo. Verdicts need file:line evidence. This is not `validate-impl` (delivery QA) and not Cursor Bugbot / Security Review (PR review).

## Local deterministic first

Start with `agentctl repo detect --cwd <repo> --json` when available. Use `rg` and `gitleaks` (if present) for secrets and XSS sinks before reading large files. Do not dump the whole tree into the model. Do not `pip install` globally.

## When to use

- User asks for a security audit, pentest-style five-flaw pass, or a PDF audit report.
- A repo (or named subtree) is the scope, not a live-only black-box test.

## When not to use

- Staged/unstaged delivery QA, deslop, or requirement fit — use [validate-impl](../validate-impl/SKILL.md).
- Syntax + commit message — use `lint-and-draft-commit-message`.
- Skill supply-chain scan — use [skillspector](../skillspector/SKILL.md).
- Inventing findings without code. If a category does not apply to the stack, say so; do not force hits.

## Inputs

| Input | Required | Notes |
| ------- | ---------- | -------- |
| Repo / cwd | yes | Default: current workspace root |
| Scope | no | Subtree or app if the user names one |
| Language | no | English default. If the user writes in Portuguese or asks pt-BR, follow [references/pt-br.md](references/pt-br.md) for PDF path, titles, and issue copy |

## Workflow

```md
Audit Progress
- [ ] 1. Detect stack
- [ ] 2. Map the five categories onto that stack
- [ ] 3. Local scans + systematic handler review
- [ ] 4. Record findings and strengths (code only)
- [ ] 5. Chat report (file:line)
- [ ] 6. Write artifacts + PDF under docs/security-audit/
- [ ] 7. Check the PDF; list generated paths
```

### 1. Detect stack

Identify language, framework, ORM/query builder, auth, frontend, and deploy files (Docker / CI / Helm / Terraform). State the **isolation mechanism** before judging category 1 (RLS, tenant middleware, manual `user_id` / org filter, none).

### 2. Map categories

Adapt each category to the stack equivalents. Skip a category only when the surface is absent (e.g. no frontend → say category 2/5 frontend half is n/a).

### 3. Review

Use `rg` (and `gitleaks` when on PATH) first. Then read handlers, not a random sample.

### 4. Record

Verified findings only. Also record what was checked and is **correct** (strengths). Note exploit conditions (flags, insecure config).

### 5. Chat

List findings file by file, line by line. Do not wait for the PDF to report them.

### 6–7. PDF

Write generator + report under `<repo>/docs/security-audit/`. English default path: `docs/security-audit/security-audit-report.pdf`. Spec: [references/pdf-spec.md](references/pdf-spec.md). Isolated venv only (reportlab+matplotlib, or HTML→PDF if a local headless browser / wkhtmltopdf / pandoc already exists). Rasterize pages if possible; fix unreadable tables before finishing.

## Categories

### 1. Unlocked database (tenant / owner isolation)

Missing row/tenant filter on list, search, aggregation, report, or export. In Supabase: missing or broken RLS. Elsewhere: queries that do not filter by the authenticated user or their org/workspace/tenant.

### 2. Browser-only permissions

Privileged UI gated by `isAdmin` / `canEdit` / `role` while the matching server route does not check the same privilege. Cross every frontend role gate with its endpoint.

### 3. IDOR

Fetch / mutate / delete by ID (path, query, or body) without proving the object belongs to the caller’s user or tenant. Walk **all** backend route handlers in scope.

### 4. Exposed keys (hardcoded)

API keys, tokens, passwords, signing secrets (JWT, webhooks), private keys, default credentials in source, configs, compose, charts, CI, scripts, docs. Watch `${VAR:-default-secret}` and missing startup rejection of those defaults. Check git history and frontend bundles.

### 5. Unprocessed input (XSS)

Frontend: `innerHTML` / `dangerouslySetInnerHTML` / `v-html` / `[innerHTML]`, unsanitized markdown/HTML, user-controlled `href`/`src` (`javascript:`), `eval` / `new Function`. Backend: user input in email HTML, templates, or responses without escape. Confirm whether a sanitizer exists **and** is used at the hit sites.

## Finding shape

For each finding: path, line number(s), snippet, why it is exploitable, severity (`critical` / `high` / `medium` / `low` / `informational`).

## Deliverables

1. Chat findings list (file:line).
2. PDF at the path above (or the pt-BR path).
3. Regenerator script kept next to the PDF.
4. Paths of every generated file.

Do not post issues to GitHub unless the user asks. The PDF already carries copy-paste issue bodies.
