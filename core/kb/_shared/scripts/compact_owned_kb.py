#!/usr/bin/env python3
"""KB compaction helpers: slice fat How-tos, add frontmatter, write llm-index.md.

Do not re-run main() — already applied 2026-08-15. Future agents: read
kb/_shared/How-to-compact-kb-skills-and-offline-reference.md and call
write_llm_index() only (v2 chooser + nested folder indexes via llm_index.py).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

KB = Path("${HOME}/.agents/kb")
SKIP_NAMES = {"llm-index.md", "How-to-author-ai-howtos.md"}

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from llm_index import write_bucket_indexes  # noqa: E402


def tokens(text: str) -> int:
    return max(1, len(text) // 4)


def write_llm_index(bucket: Path) -> None:
    write_bucket_indexes(bucket)



def split_worklog() -> None:
    src = KB / "worklog/README.md"
    text = src.read_text(encoding="utf-8")
    # extract major sections
    def section(name: str, until: str | None) -> str:
        pat = rf"^## {re.escape(name)}\n"
        m = re.search(pat, text, re.M)
        if not m:
            return ""
        start = m.start()
        if until:
            m2 = re.search(rf"^## {re.escape(until)}\n", text[m.end() :], re.M)
            end = m.end() + m2.start() if m2 else len(text)
        else:
            end = len(text)
        return text[start:end].rstrip() + "\n"

    slack = section("MCP discovery", "Jira collection") + "\n" + section("Slack collection", "Jira collection")
    # MCP discovery until Slack is included in first call if until is Slack... fix:
    mcp = section("MCP discovery", "Slack collection")
    slack_only = section("Slack collection", "Jira collection")
    jira = section("Jira collection", "Collection status model")
    status = section("Collection status model", "Post-run learning protocol")
    learn = section("Post-run learning protocol", "Changelog")
    changelog = section("Changelog", None)
    seq = section("Run sequence", "Stable local paths")
    paths = section("Stable local paths", "MCP discovery")

    def wrap(fid: str, title: str, body: str) -> str:
        return (
            "---\n"
            f"id: {fid}\n"
            "when_skills: [generate-worklogs]\n"
            "read: section\n"
            "prose: caveman-lite\n"
            "---\n\n"
            f"# {title}\n\n"
            + re.sub(r"^## ", "### ", body, flags=re.M)
        )

    (KB / "worklog/slack.md").write_text(
        wrap("worklog-slack", "Worklog Slack + MCP discovery", mcp + "\n" + slack_only),
        encoding="utf-8",
    )
    (KB / "worklog/jira.md").write_text(
        wrap("worklog-jira", "Worklog Jira collection and posting", jira),
        encoding="utf-8",
    )
    readme = (
        "---\n"
        "id: worklog-readme\n"
        "when_skills: [generate-worklogs]\n"
        "read: whole\n"
        "prose: caveman-lite\n"
        "---\n\n"
        "# Worklog operations\n\n"
        "Skill `generate-worklogs` owns output, attribution, and safety. "
        "This folder owns collectors and live tool usage.\n\n"
        "Last verified: 2026-08-14\n\n"
        "| Need | File |\n"
        "|------|------|\n"
        "| Slack / MCP discovery | [slack.md](slack.md) |\n"
        "| Jira collection and posting | [jira.md](jira.md) |\n"
        "| llm-index | [llm-index.md](llm-index.md) |\n\n"
        + seq
        + "\n"
        + paths
        + "\n"
        + status
        + "\n"
        + learn
        + "\n"
        + changelog
    )
    src.write_text(readme, encoding="utf-8")


def add_commands_index() -> None:
    path = KB / "implementation/enonic-cli/commands.md"
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        return
    cmds = re.findall(r"^### (enonic .+)$", text, re.M)
    rows = "\n".join(f"| `{c}` | `### {c}` |" for c in cmds)
    fm = (
        "---\n"
        "id: enonic-cli-commands\n"
        "when_skills: [use-enonic-cli]\n"
        "read: section\n"
        "prose: caveman-lite\n"
        "---\n\n"
        "# Enonic CLI command reference\n\n"
        "Open only the matching `### enonic …` heading. Do not read this whole file.\n\n"
        "| Command | Heading |\n"
        "|---------|---------|\n"
        f"{rows}\n\n"
    )
    # drop original H1 if present
    text = re.sub(r"^# Enonic CLI — Full Command Reference\n+", "", text)
    path.write_text(fm + text, encoding="utf-8")


SCOPE_RE = re.compile(
    r"^(# .+)\n+(?:\*\*Scope:\*\*[^\n]*\n)+(?:\*\*Applies to:\*\*[^\n]*\n)?(?:\*\*Related:\*\*[^\n]*\n)?(?:\*\*CLI version baseline:\*\*[^\n]*\n)?\n?",
    re.M,
)


def add_frontmatter(path: Path, bucket: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        return False
    if path.name in SKIP_NAMES:
        return False
    m = re.match(r"^# (.+)\n", text)
    title = m.group(1) if m else path.stem
    slug = path.stem.lower()
    scope = re.search(r"\*\*Scope:\*\*\s*(.+)", text)
    applies = re.search(r"\*\*Applies to:\*\*\s*(.+)", text)
    when = []
    if applies:
        when = re.findall(r"`([^`]+)`", applies.group(1))
    fm_when = ", ".join(when[:8]) if when else ""
    body = SCOPE_RE.sub(r"\1\n\n", text, count=1)
    body = re.sub(r"^## Purpose\n\n(?:.*?\n)+?(?=^## )", "", body, count=1, flags=re.M | re.S)
    fm = (
        "---\n"
        f"id: {slug}\n"
        f"when_skills: [{fm_when}]\n"
        "read: section\n"
        "prose: caveman-lite\n"
        "---\n\n"
    )
    path.write_text(fm + body.lstrip(), encoding="utf-8")
    return True


def remainder_frontmatter() -> int:
    n = 0
    for f in KB.rglob("*.md"):
        if "offline-reference" in f.parts:
            continue
        if f.name in SKIP_NAMES or f.name == "llm-index.md":
            continue
        if add_frontmatter(f, f.relative_to(KB).parts[0]):
            n += 1
    return n


def main() -> None:
    split_worklog()
    add_commands_index()
    n = remainder_frontmatter()
    for bucket in ["_shared", "implementation", "testing", "validation", "worklog"]:
        write_llm_index(KB / bucket)
    print(f"frontmatter_added={n}")


if __name__ == "__main__":
    main()
