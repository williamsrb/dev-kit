#!/usr/bin/env python3
"""Project the Impeccable agents from the Codex build into Claude and Codex.

The Codex build of the skill is the only one that ships the agent definitions next to
the skill version, so it is the source:

  skills-vendor/codex/impeccable/agents/*.toml
    -> ~/.agents/agents/<name>.md      generated for Claude (~/.claude/agents links to that dir)
    -> ~/.codex/agents/<file>.toml     symlink; stale hyphen-named copies are removed

Cursor ships its own .md copies of the Impeccable agents in ~/.cursor/agents; they are not touched.

The harness's own agents (agents/image-describer.md, Claude format) are the source for the other two vendors:

  agents/image-describer.md
    -> ~/.codex/agents/image_describer.toml    generated; model and effort from the ROLES.md deterministic cell
    -> ~/.cursor/agents/image-describer.md     generated

  sync-agent-projections.py            # report drift, change nothing (exit 1 on drift)
  sync-agent-projections.py --apply    # write, link, prune

Python 3.12, standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

HOME = Path.home()
SRC = HOME / ".agents/skills-vendor/codex/impeccable/agents"
CLAUDE_DIR = HOME / ".agents/agents"
CODEX_DIR = HOME / ".codex/agents"
CURSOR_DIR = HOME / ".cursor/agents"
ROLES = HOME / ".agents/skills-vendor/ROLES.md"
OWN_AGENTS = ("image-describer",)

READ_ONLY = {"impeccable_finish_reviewer"}
FULL_TOOLS = "Read, Write, Edit, Bash, Glob, Grep"
READ_TOOLS = "Read, Bash, Glob, Grep"
MAX_TURNS = 12


def claude_body(body: str) -> str:
    """The Codex body minus its Codex-only lines, with the skill path of Claude."""
    lines = [line for line in body.splitlines() if not line.startswith("Codex: ")]
    return "\n".join(lines).replace(".agents/skills/", ".claude/skills/").strip() + "\n"


def claude_md(spec: dict) -> str:
    description = spec["description"]
    if re.search(r": |#", description):
        description = json.dumps(description)
    tools = READ_TOOLS if spec["name"] in READ_ONLY else FULL_TOOLS
    head = [
        f"name: {spec['name'].replace('_', '-')}",
        f"description: {description}",
        f"tools: {tools}",
        "model: inherit",
        f"effort: {spec['model_reasoning_effort']}",
        f"maxTurns: {MAX_TURNS}",
    ]
    return "---\n" + "\n".join(head) + "\n---\n" + claude_body(spec["developer_instructions"])


def own_agent(name: str, claude_dir: Path) -> tuple[dict[str, str], str]:
    """Frontmatter fields and body of a harness agent in the Claude format."""
    _, head, body = (claude_dir / f"{name}.md").read_text(encoding="utf-8").split("---\n", 2)
    fields = {}
    for line in head.splitlines():
        key, _, value = line.partition(": ")
        fields[key] = json.loads(value) if value.startswith('"') else value
    return fields, body.strip() + "\n"


def codex_cell() -> tuple[str, str]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import agentctl_bench
    model, effort = re.findall(r"`([^`]+)`", agentctl_bench.read_role_cells(ROLES)[("deterministic", "codex")])[:2]
    return model, effort


def codex_toml(fields: dict[str, str], body: str) -> str:
    model, effort = codex_cell()
    return (f'name = "{fields["name"].replace("-", "_")}"\ndescription = {json.dumps(fields["description"])}\n'
            f'model = "{model}"\nmodel_reasoning_effort = "{effort}"\nsandbox_mode = "read-only"\n'
            f"developer_instructions = \'\'\'\n{body}\'\'\'\n")


def cursor_md(fields: dict[str, str], body: str) -> str:
    return ("---\n" f"name: {fields['name']}\ndescription: {json.dumps(fields['description'])}\n"
            "model: fast\nreadonly: true\n---\n" + body)


def own_actions(claude_dir: Path, codex_dir: Path, cursor_dir: Path) -> list[tuple[str, Path, object]]:
    actions: list[tuple[str, Path, object]] = []
    for name in OWN_AGENTS:
        fields, body = own_agent(name, claude_dir)
        for path, text in ((codex_dir / f"{name.replace('-', '_')}.toml", codex_toml(fields, body)),
                           (cursor_dir / f"{name}.md", cursor_md(fields, body))):
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                actions.append(("write", path, text))
    return actions


def plan(src: Path = SRC, claude_dir: Path = CLAUDE_DIR, codex_dir: Path = CODEX_DIR,
         cursor_dir: Path = CURSOR_DIR) -> list[tuple[str, Path, object]]:
    """Actions as (verb, path, payload): write (text), link (target), remove."""
    actions: list[tuple[str, Path, object]] = []
    for toml in sorted(src.glob("*.toml")):
        spec = tomllib.loads(toml.read_text(encoding="utf-8"))
        md = claude_dir / f"{toml.stem.replace('_', '-')}.md"
        text = claude_md(spec)
        if not md.is_file() or md.read_text(encoding="utf-8") != text:
            actions.append(("write", md, text))

        link = codex_dir / toml.name
        if not (link.is_symlink() and link.readlink() == toml):
            actions.append(("link", link, toml))
        legacy = codex_dir / f"{toml.stem.replace('_', '-')}.toml"
        if legacy.exists() or legacy.is_symlink():
            actions.append(("remove", legacy, None))
    return actions + own_actions(claude_dir, codex_dir, cursor_dir)


def apply(actions: list[tuple[str, Path, object]]) -> None:
    for verb, path, payload in actions:
        if verb == "write":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(payload), encoding="utf-8")
        elif verb == "link":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.unlink(missing_ok=True)
            path.symlink_to(Path(str(payload)))
        else:
            path.unlink()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the changes (default: report only)")
    args = ap.parse_args()
    if not SRC.is_dir():
        print(f"no agent source at {SRC}", file=sys.stderr)
        return 1
    actions = plan()
    for verb, path, _ in actions:
        print(f"  {verb:6} {path}")
    if not actions:
        print("  up to date")
        return 0
    if args.apply:
        apply(actions)
        return 0
    print("  (dry run, re-run with --apply)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
