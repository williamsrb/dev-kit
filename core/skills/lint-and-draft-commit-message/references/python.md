# Python stack

Load this file only when the delivery includes `*.py`. Do not load it because the repo has `pyproject.toml` if no Python files changed.

## Classify

| Class | Typical paths | Action |
|-------|---------------|--------|
| **Delivery Python** | `*.py` in the delivery, including skill helpers under `skills/*/scripts/` and `bin/` | Validate and fix |
| **Skip** | `.venv`, `venv`, `__pycache__`, generated, vendored | Do not validate/fix |

Prefer project-native config (`pyproject.toml` `[tool.ruff]`, `ruff.toml`, `setup.cfg`) over global defaults.

## Parse and lint

For each delivery `.py` file:

1. **Parse** — `python3 -m py_compile <file>`. Treat a non-zero exit as a Blocker and fix it.
2. **Ruff** — already batched by `agentctl checks run` (check name `ruff`). If that step failed on delivery files, apply the smallest fix. `ruff check --fix` is allowed **only** on delivery-scope `.py` files for auto-fixable errors. Do not reformat the whole tree. Do not `ruff format` unless the project already formats that way and the failure is in the delivery.
3. **Typecheck** — run `mypy` / `pyright` only when the project already declares it (config or a Makefile/`npm`/script target). Fix errors that originate in delivery-scope files only. Skip and say so when no config exists.
4. **Imports** — confirm imported names exist; fix missing stdlib/project imports. Do **not** `pip install` to make an import resolve.

## Semantic checks (Python)

- Undefined names and unused leftovers from the delivery hunks.
- `sys.path` hacks and implicit relative imports that the surrounding module does not use.
- Scripts that shell out: keep `subprocess`/`pathlib` conventions of this repo; do not rewrite a working helper into bash.

## Fix policy (Python)

Fix parse errors, ruff **errors**, and broken imports in delivery files. Do not expand to a package-wide refactor, do not add a new linter config, and do not add dependencies.

## Report section

Append only when this file was loaded:

```markdown
### Python

&nbsp;&nbsp;&nbsp;&nbsp;✅&nbsp;&nbsp;&nbsp; <file>: PASS

&nbsp;&nbsp;&nbsp;&nbsp;⛔&nbsp;&nbsp;&nbsp; <file>: FAIL. <issue → remaining after fixes>

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp; py_compile/ruff/mypy: <command(s) run>, or SKIPPED (<reason>)
```
