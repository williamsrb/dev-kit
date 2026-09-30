# Generic stack

Load this file when the delivery has source that is **not** classified as Python (`*.py`), **not** classified as PHP (`*.php` / `*.phtml`), and **not** classified as Enonic (see [enonic.md](enonic.md)). Typical: Node/TS apps, shell, YAML/JSON, markdown, CI.

Do not load it for a Python-only, PHP-only, or Enonic-only delivery. If those files appear next to generic files, load this file **and** the matching stack file; do not re-apply Python, PHP, or Enonic rules here.

## Validation by file type

| Area | Guidance |
|------|----------|
| **JS / TS source** (not Enonic-classified) | Braces, semicolons, parse check, import/require resolution, undefined calls. `node --check` on `.js` when Node is available. `tsc --noEmit` when the project has a tsconfig / typecheck script; fix errors in delivery scope only. |
| **Config / CI (JSON, YAML)** | Valid structure; fix trailing commas, bad indentation, broken keys. `agentctl checks run` covers `yq` for YAML. |
| **Shell** | `shellcheck` via `agentctl checks run`. `shfmt` is **not** in that batch — run it on delivery `.sh` / `.bash` when available. |
| **Docs / markdown** | Broken links in changed sections; no fabricated changelog entries. `lychee` is optional and not in `agentctl checks run`. |
| **All text** | Secrets in diff, wrong paths, obvious dead code in changed hunks. |

## Extra tools

Keep as their own steps when relevant: `shfmt`, `lychee`, `ast-grep`. Do not invent a typecheck for a language the project does not already compile.

## Report section

Generic findings go in the shared **Syntax & semantic validation** and **Linter** sections. No extra heading.
