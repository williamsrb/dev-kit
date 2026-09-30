# Enonic / React4XP stack

Load this file only when the delivery includes Enonic-classified files (table below). Do not load it because detect reported `enonic` / `react4xp` / `gradle` if those trees were not in the delivery.

## Classify

| Class | Typical paths / extensions | Rules |
|-------|----------------------------|--------|
| **Backend Enonic JS** | Controllers, services, libs under `xp/` as `*.js` (not React4XP entries/assets) | Enonic CommonJS + ES5.1 (+ allowed extras) |
| **XP / CMS TypeScript** | `*.ts` under `xp/src/main/resources/` (processors, libs, types) — not React view `.tsx` | Generic TS syntax/semantic + `tsconfig.xp.nashorn.json` |
| **React4XP views** | `*.tsx`, React4XP components/entries/utils | Generic TS/TSX syntax/semantic + `tsconfig.react4xp.json` |
| **XP descriptors** | `*.xml` / `*.yml` under `xp/src/main/resources/` or `src/main/resources/` | Structure only; `xmllint` / `yq` via `agentctl checks run`; `xmlstarlet` when the loaded delivery needs it |
| **Other frontend JS** | Browser bundles, `assets/js/`, client utilities | Generic JS checks only (no Enonic ES5.1) |
| **Skip** | Generated/bundled assets, `node_modules`, build output | Do not validate/fix |

**Never** apply Enonic backend CommonJS/ES5.1 rules to TypeScript (`*.ts` / `*.tsx`), React4XP view code, Next.js, or browser bundles.

Python files in the same delivery belong to [python.md](python.md), not this file.

## Backend JS validation rules (Enonic XP 7.16)

For each **backend Enonic JS** file only:

- CommonJS only (`require`, `exports`, `module.exports`); no ESM `import`/`export`.
- Syntax: ES5.1 + allowed extras: arrow functions; template strings (not containing regex patterns); `let`/`const`; default parameters; computed property names; object shorthand.
- Flag and **fix** unsupported modern syntax when a safe ES5.1-compatible rewrite exists within the delivery.

If no backend JS files are in the delivery, state that and skip Enonic-specific rules.

Parse check: `node --check` on backend `.js` when Node is available.

## React4XP / TypeScript validation

When the delivery includes `*.ts` or `*.tsx` in an Enonic/React4XP tree:

1. Apply the mandatory syntax/semantic checks from SKILL.md (imports allowed; modern TS/JS is fine).
2. Prefer a root **Makefile** typecheck target if one exists; otherwise from the XP app dir:
   - XP/CMS `.ts` → `npx tsc --noEmit -p tsconfig.xp.nashorn.json` (or `npm run check:types:xp`).
   - React4XP `.tsx` → `npx tsc --noEmit -p tsconfig.react4xp.json` (or `npm run check:types:react4xp`).
   - Both → run both (or aggregating `npm run check:types`).
3. Fix **errors that originate in delivery-scope files** only.
4. Treat delivery-scoped `tsc` errors as blockers.
5. Skip typecheck only when no `.ts`/`.tsx` are in the delivery — say so in the report.

Do **not** rewrite TS/TSX to ES5.1 CommonJS style.

## Extra tools

`xmlstarlet` is not in `agentctl checks run`. Use it only when the delivery includes XP descriptors that need it. `ast-grep` stays optional.

## Report sections

Append only when this file was loaded:

```markdown
### Enonic backend JS (XP 7.16)

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <file>: PASS

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; <file>: FAIL. <issue → remaining after fixes>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; <file>: SKIPPED (<reason>)

### React4XP / TypeScript

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <file or tsc project>: PASS

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; <file or tsc project>: FAIL. <issue → remaining after fixes>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; tsc: <command(s) run>, or SKIPPED (<reason>)
```
