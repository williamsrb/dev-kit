---
id: how-to-author-ai-howtos
when_skills: []
inputs: [owned How-to under ~/.agents/kb]
outputs: [agent-first How-to]
stop_if: [file is a fenced template or skill name field]
read: whole
prose: caveman-lite
---

# Author AI How-tos

Owned KB is for agents. Humans are not the primary reader. Do not keep a second human-readable copy.

## Structure

```yaml
---
id: how-to-<slug>
when_skills: [<canonical skill directory names or aliases>]
inputs: [...]
outputs: [...]
stop_if: [...]
read: section | whole
prose: caveman-lite
---
```

`read: whole` only when the file is under ~400 tokens. Catalogs stay `read: section`.

`when_skills` is documentation for humans and the index `skills` column. It does **not** auto-load this How-to. Use canonical skill directory names or `metadata.aliases`. Globs, URLs, ticket keys, and source paths are dropped at index time.

Body order:

1. `#` verb-phrase title
2. `## Procedure` — numbered steps
3. `## Pitfalls` — failure modes and stop conditions
4. Commands/tables as needed
5. `examples.md` sibling only when a worked sample is required; do not embed long tutorials

Do not use Scope / Applies to / Related as H2 prose. That data belongs in frontmatter. Do not restate the skill's "when to use" contract.

## Caveman-lite (required)

Same register as `~/.agents/rules/token-efficiency-chat.mdc` chat rules:

- Drop filler and hedging.
- Keep full sentences and articles.
- Paths, issue keys, SHAs, commands, and error strings stay exact.
- Never stylistically compress fenced commands or code.
- Never use stock Caveman full/ultra fragments. Negations stay explicit (`Do not fix the delivery toward a forbidden Figma reading`, not `No fix Figma`).

## Routing

Each bucket has a thin `llm-index.md` chooser (`path<TAB>tokens<TAB>topic<TAB>skills<TAB>keywords`). Folder rows end in `llm-index.md` — open the matching project/topic folder index (for example `testing/acme-group/` or `testing/_shared/`), not sibling projects. Then open only How-tos whose topic/keywords match. Do not open a whole catalog "just in case".

Keywords come from the filename and H1, not from Procedure/Pitfalls headings. Rebuild with `python3 ~/.agents/kb/_shared/scripts/llm_index.py`.

Offline-reference catalogs use the same format. Fat catalogs (XP8, XP7, Godot) are themselves choosers (`cms`/`code`/`platform`, `api`/`framework`, `classes`/`tutorials`). Compact conversion artifacts and Sphinx chrome only; keep API signatures, tables, and fenced code exact. Do not rewrite vendor API pages into How-to procedure form.

Re-runs and script safety: [How-to-compact-kb-skills-and-offline-reference.md](How-to-compact-kb-skills-and-offline-reference.md).
