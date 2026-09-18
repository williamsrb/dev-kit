# PDF spec (English default)

Output: `<repo>/docs/security-audit/security-audit-report.pdf`. Keep the generator in the same directory.

Do not install packages globally. Use a venv under `docs/security-audit/.venv` (reportlab + matplotlib) or an already-installed HTML→PDF tool.

A4, ~2 cm margins, header/footer with report name and page number.

Palette: critical `#B91C1C`, high `#EA580C`, medium `#D97706`, low `#2563EB`, strength `#059669`.

## Pages

1. **Cover** — title `Security Audit Report — <project name>`, date, audited scope, one-line method note (how each category mapped to the detected stack).
2. **Executive summary** — counts by severity; donut by severity; bar by category.
3. **Strengths and weaknesses** — protected surfaces with evidence; central risks.
4. **Findings table** — Severity | File:line | Description, color-coded severity chip, grouped by category.
5. **Recommendations** — P1, P2, P3…
6. **GitHub issues** — one copy-paste Markdown issue per actionable finding (group related trivial hits). Delimit with `--- ISSUE n ---` / `--- END ISSUE n ---`.

## Issue body

- Title: `[Security] <short flaw>`
- Labels: `security` + severity
- Problem and why exploitable
- Evidence: `file:line` + snippet
- Impact
- Suggested fix
- Acceptance criteria (verifiable checklist)
