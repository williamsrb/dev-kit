# PHP stack

Load this file only when the delivery includes `*.php` or `*.phtml`. Do not load it because the repo has `composer.json` if no PHP files changed.

## Classify

| Class | Typical paths | Action |
|-------|---------------|--------|
| **Delivery PHP** | `*.php`, `*.phtml` in the delivery | Validate and fix |
| **Skip** | `vendor/`, generated, bundled | Do not validate/fix |

Prefer project-native config (`phpcs.xml`, `phpstan.neon`, `psalm.xml`, `pint.json`, `.php-cs-fixer.php`) over global defaults.

## Parse and lint

For each delivery PHP file:

1. **Parse** — `php -l <file>` (batched by `agentctl checks run`, check name `php`). Treat a non-zero exit as a Blocker and fix it. `php -l` is per-file; do not pass a whole tree as one argv.
2. **Project linters** — run only tools the project already declares (composer script, Makefile, or config): `phpcs`, `phpstan`, `psalm`, `pint`, `php-cs-fixer`. Fix errors that originate in delivery-scope files only. Skip and say so when no config/script exists.
3. **Do not** `composer require` a linter to make a check run.

## Semantic checks (PHP)

- Undefined functions/classes and unused leftovers from the delivery hunks.
- `require` / `include` / `use` paths that do not resolve in this tree (after `vendor/` autoload, if the project has one).
- Modern syntax the project's PHP version does not allow only when `composer.json` `require.php` (or a CI image) states that version.

## Fix policy (PHP)

Fix parse errors and linter **errors** in delivery files. Do not expand to a package-wide refactor, do not add a new linter config, and do not add dependencies.

## Report section

Append only when this file was loaded:

```markdown
### PHP

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <file>: PASS

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; <file>: FAIL. <issue → remaining after fixes>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; php -l / phpcs / phpstan: <command(s) run>, or SKIPPED (<reason>)
```
