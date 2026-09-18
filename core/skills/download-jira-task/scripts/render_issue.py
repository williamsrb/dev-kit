#!/usr/bin/env python3
"""Render a saved Jira connector payload as download-jira-task PRD Markdown.

Handles the three body shapes the Atlassian MCP tools return:

  * ADF   - node tree (``plugin_atlassian`` getJiraIssue, default format)
  * HTML  - markup string (``atlassian-rovo-preview`` getJiraIssue,
            ``appliedContentFormat: "html"``)
  * Markdown - plain string (``responseContentFormat: "markdown"``)

Output follows the template in SKILL.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

JIRA_BASE = "https://example.atlassian.net/browse"
PRD_ROOT = Path.home() / ".agents/prds"

# SKILL.md mandates skipping this exact author (GitLab commit/MR mention spam).
SKIP_AUTHORS = {"Solutions Jira x GitLab"}

# Broader automation filter, opt-in via --strict-bots. Left off by default
# because it also matches humans whose display name contains e.g. "bot".
BOT_RE = re.compile(r"bot|gitlab|github|jenkins|bamboo|automation", re.IGNORECASE)

BLOB_RE = re.compile(r"blob:https://media\.[^\s\)\"']+")
# An <img> whose src is a blob becomes a Markdown image first; strip the
# whole wrapper, otherwise the replacement text nests inside its parens.
BLOB_IMG_RE = re.compile(r"!\[[^\]]*\]\(\s*blob:https://media\.[^\)]*\)")
SMARTLINK_RE = re.compile(
    r"<custom\b[^>]*\bdata-type=[\"']smartlink[\"'][^>]*\bhref=[\"']([^\"']+)[\"'][^>]*>.*?</custom>",
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")


# --------------------------------------------------------------------------
# payload navigation
# --------------------------------------------------------------------------

def find_issue(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if "key" in value and ("fields" in value or "summary" in value):
            return value
        for key in ("issue", "data", "structuredContent", "result"):
            found = find_issue(value.get(key))
            if found:
                return found
        for child in value.values():
            found = find_issue(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_issue(child)
            if found:
                return found
    return None


def declared_format(payload: Any) -> str | None:
    """Read appliedContentFormat / responseContentFormat if the payload states one."""
    if isinstance(payload, dict):
        for key in ("appliedContentFormat", "responseContentFormat", "contentFormat"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        for child in payload.values():
            found = declared_format(child)
            if found:
                return found
    elif isinstance(payload, list):
        for child in payload:
            found = declared_format(child)
            if found:
                return found
    return None


def detect_format(value: Any, declared: str | None) -> str:
    """Classify one body value as 'adf', 'html' or 'markdown'."""
    if isinstance(value, dict):
        return "adf"
    if not isinstance(value, str):
        return "markdown"
    if declared in {"html", "adf", "markdown"} and declared != "adf":
        return declared
    return "html" if TAG_RE.search(value) else "markdown"


# --------------------------------------------------------------------------
# ADF -> Markdown
# --------------------------------------------------------------------------

def text_with_marks(node: dict[str, Any]) -> str:
    text = str(node.get("text", ""))
    marks = {mark.get("type") for mark in node.get("marks", []) if isinstance(mark, dict)}
    if "code" in marks:
        text = f"`{text}`"
    if "strong" in marks:
        text = f"**{text}**"
    if "em" in marks:
        text = f"*{text}*"
    for mark in node.get("marks", []):
        if mark.get("type") == "link" and mark.get("attrs", {}).get("href"):
            text = f"[{text}]({mark['attrs']['href']})"
    return text


def adf(node: Any, depth: int = 0) -> str:
    """Walk an ADF node tree.

    A bare string is NOT valid inside ADF content. Earlier versions returned it
    unchanged, which let an HTML description pass straight through into the PRD
    with its tags intact. Route strings through body_to_md() instead of here.
    """
    if node is None:
        return ""
    if isinstance(node, str):
        raise TypeError("bare string reached adf(); classify it with detect_format() first")
    if isinstance(node, list):
        return "".join(adf(child, depth) for child in node)
    if not isinstance(node, dict):
        return str(node)
    kind = node.get("type")
    content = node.get("content", [])
    if kind == "text":
        return text_with_marks(node)
    if kind == "hardBreak":
        return "\n"
    if kind == "mention":
        return "@" + str(node.get("attrs", {}).get("text", "user")).lstrip("@")
    if kind in {"inlineCard", "blockCard"}:
        return str(node.get("attrs", {}).get("url", ""))
    if kind == "heading":
        level = int(node.get("attrs", {}).get("level", 2))
        return f"{'#' * max(1, min(level, 6))} {adf(content, depth).strip()}\n\n"
    if kind == "paragraph":
        return adf(content, depth).strip() + "\n\n"
    if kind == "codeBlock":
        language = node.get("attrs", {}).get("language", "")
        return f"```{language}\n{adf(content, depth).strip()}\n```\n\n"
    if kind in {"bulletList", "orderedList"}:
        ordered = kind == "orderedList"
        lines = []
        for index, item in enumerate(content, 1):
            prefix = f"{index}." if ordered else "*"
            item_text = adf(item.get("content", []), depth + 1).strip().replace("\n\n", "\n")
            lines.append(f"{'  ' * depth}{prefix} {item_text}")
        return "\n".join(lines) + "\n\n"
    if kind == "listItem":
        return adf(content, depth)
    if kind == "blockquote":
        lines = adf(content, depth).strip().splitlines()
        return "\n".join(f"> {line}" for line in lines) + "\n\n"
    if kind == "rule":
        return "---\n\n"
    return adf(content, depth)


# --------------------------------------------------------------------------
# HTML -> Markdown
# --------------------------------------------------------------------------

class _HtmlToMarkdown(HTMLParser):
    """Stdlib fallback for the tag set Jira actually emits.

    Deliberately narrow: markdownify handles this better and is preferred when
    importable. This exists so the skill keeps working on a machine without it.
    """

    INLINE = {
        "strong": "**", "b": "**",
        "em": "*", "i": "*",
        "code": "`",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.list_stack: list[dict[str, Any]] = []
        self.href: str | None = None
        self.in_pre = False
        # Jira wraps list-item text in <p>; that must not break the item.
        self.li_open = False

    def _emit(self, text: str) -> None:
        self.parts.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = dict(attrs)
        if tag in self.INLINE:
            self._emit(self.INLINE[tag])
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._emit("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "p":
            if self.li_open:
                self.li_open = False
            else:
                self._emit("\n\n")
        elif tag == "br":
            self._emit("\n")
        elif tag == "hr":
            self._emit("\n\n---\n\n")
        elif tag == "a":
            self.href = mapping.get("href")
            self._emit("[")
        elif tag == "img":
            alt = mapping.get("alt") or "image"
            self._emit(f"![{alt}]({mapping.get('src', '')})")
        elif tag == "pre":
            self.in_pre = True
            self._emit("\n\n```\n")
        elif tag in {"ul", "ol"}:
            self.list_stack.append({"ordered": tag == "ol", "n": 0})
            self._emit("\n")
        elif tag == "li" and self.list_stack:
            frame = self.list_stack[-1]
            frame["n"] += 1
            indent = "  " * (len(self.list_stack) - 1)
            marker = f"{frame['n']}." if frame["ordered"] else "*"
            # Keep lists tight: drop any pending blank line between items.
            while frame["n"] > 1 and self.parts and self.parts[-1].strip() == "" and "\n" in self.parts[-1]:
                self.parts.pop()
            self._emit(f"\n{indent}{marker} ")
            self.li_open = True
        elif tag == "blockquote":
            self._emit("\n\n> ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.INLINE:
            self._emit(self.INLINE[tag])
        elif tag == "p":
            self._emit("\n" if self.list_stack else "\n\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}:
            self._emit("\n\n")
        elif tag == "a":
            self._emit(f"]({self.href or ''})")
            self.href = None
        elif tag == "pre":
            self.in_pre = False
            self._emit("\n```\n\n")
        elif tag == "li":
            self.li_open = False
        elif tag in {"ul", "ol"}:
            if self.list_stack:
                self.list_stack.pop()
            self._emit("\n")

    def handle_data(self, data: str) -> None:
        if self.in_pre:
            self._emit(data)
            return
        # Collapse whitespace outside <pre>; HTML newlines are not breaks.
        text = re.sub(r"\s+", " ", data)
        if text.strip() or self.parts:
            self._emit(text)

    def result(self) -> str:
        return "".join(self.parts)


def html_to_md(text: str) -> str:
    """Convert HTML to Markdown. Uses markdownify when available."""
    try:
        from markdownify import markdownify
    except ImportError:
        parser = _HtmlToMarkdown()
        parser.feed(text)
        parser.close()
        return html.unescape(parser.result())
    return markdownify(text, heading_style="ATX", bullets="*")


# --------------------------------------------------------------------------
# shared body pipeline
# --------------------------------------------------------------------------

def body_to_md(value: Any, declared: str | None) -> str:
    if value is None:
        return ""
    fmt = detect_format(value, declared)
    if fmt == "adf":
        text = adf(value)
    elif fmt == "html":
        text = SMARTLINK_RE.sub(r"\1", str(value))
        text = html_to_md(text)
    else:
        text = str(value)
    text = BLOB_IMG_RE.sub("(image attachment — see ## Attachments)", text)
    text = BLOB_RE.sub("(image attachment — see ## Attachments)", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def attachments_dir(key: str, prd_root: Path | None = None) -> Path:
    root = (prd_root or PRD_ROOT).expanduser()
    return root / key / "attachments"


def safe_attachment_filename(attachment_id: str, filename: str) -> str:
    base = Path(str(filename or "attachment")).name.replace("\x00", "").strip() or "attachment"
    return f"{attachment_id}-{base}"


def list_attachments(
    fields: dict[str, Any],
    key: str,
    prd_root: Path | None = None,
) -> list[dict[str, Any]]:
    raw = fields.get("attachment") or []
    if not isinstance(raw, list):
        return []
    dest = attachments_dir(key, prd_root)
    items = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        attachment_id = str(entry.get("id") or "").strip()
        if not attachment_id:
            continue
        filename = str(entry.get("filename") or "attachment")
        stored = safe_attachment_filename(attachment_id, filename)
        items.append(
            {
                "id": attachment_id,
                "filename": filename,
                "storedName": stored,
                "outputPath": str(dest / stored),
                "size": entry.get("size"),
                "mimeType": entry.get("mimeType") or "",
            }
        )
    return items


def name(node: Any) -> str:
    if isinstance(node, dict):
        return str(
            node.get("displayName") or node.get("name") or node.get("accountId") or ""
        )
    return str(node or "")


def keep_comment(author: str, include_bots: bool, strict_bots: bool) -> bool:
    if include_bots:
        return True
    if author in SKIP_AUTHORS:
        return False
    if strict_bots and BOT_RE.search(author):
        return False
    return True


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def render(
    payload: dict[str, Any],
    include_bots: bool = False,
    strict_bots: bool = False,
) -> tuple[str, str, dict[str, Any]]:
    issue = find_issue(payload)
    if not issue:
        raise ValueError("could not find a Jira issue object")
    fields = issue.get("fields") or issue
    declared = declared_format(payload)
    key = str(issue.get("key") or fields.get("key") or "UNKNOWN")
    project = fields.get("project") or {}

    comments_value = fields.get("comment") or issue.get("comments") or []
    comments = (
        comments_value.get("comments", [])
        if isinstance(comments_value, dict)
        else comments_value
    )
    kept, skipped = [], 0
    for comment in comments or []:
        author = name(comment.get("author"))
        if not keep_comment(author, include_bots, strict_bots):
            skipped += 1
            continue
        kept.append(comment)

    files = list_attachments(fields, key)

    lines = [
        f"# {key} — {fields.get('summary', '')}",
        "",
        f"**Jira:** {JIRA_BASE}/{key}",
        f"**Project:** {project.get('name', '')} ({project.get('key', '')})",
        f"**Type:** {name(fields.get('issuetype'))}",
        f"**Status:** {name(fields.get('status'))}",
        f"**Priority:** {name(fields.get('priority'))}",
        f"**Reporter:** {name(fields.get('reporter')) or 'Unassigned'}",
        f"**Assignee:** {name(fields.get('assignee')) or 'Unassigned'}",
        f"**Created:** {fields.get('created', '')}",
        f"**Updated:** {fields.get('updated', '')}",
        "",
        "---",
        "",
        "## Description",
        "",
        body_to_md(fields.get("description"), declared) or "No description",
        "",
        "---",
        "",
        f"## Comments ({len(kept)})",
        "",
    ]
    if not kept:
        lines += ["No comments.", ""]
    for comment in kept:
        created = str(comment.get("created", ""))[:10]
        lines += [
            f"### Comment {comment.get('id', '')} — {name(comment.get('author'))} — {created}",
            "",
            body_to_md(comment.get("body"), declared),
            "",
        ]
    lines += ["---", "", f"## Attachments ({len(files)})", ""]
    if not files:
        lines += ["No attachments.", ""]
    else:
        dest = attachments_dir(key)
        lines += [f"Directory: `{dest}`", ""]
        for item in files:
            size = item.get("size")
            size_bit = f", {size} bytes" if size is not None else ""
            mime = item.get("mimeType") or "unknown"
            lines += [
                f"- `{item['storedName']}` — {item['filename']} ({mime}{size_bit}); id `{item['id']}`",
                "",
            ]
    lines += ["---", "", f"*Exported from Jira on {dt.date.today().isoformat()}*", ""]

    metadata = {
        "key": key,
        "summary": str(fields.get("summary", "")),
        "comments": len(kept),
        "attachments": len(files),
        "skipped_bot_comments": skipped,
        "format": detect_format(fields.get("description"), declared),
    }
    return key, "\n".join(lines), metadata


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def write(payload: dict[str, Any], target: Path, args: argparse.Namespace) -> dict[str, Any]:
    key, markdown, metadata = render(payload, args.include_bots, args.strict_bots)
    target = target.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown, encoding="utf-8")
    return {"status": "written", "output": str(target), **metadata}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--batch", type=Path, nargs="+", metavar="PAYLOAD")
    parser.add_argument("--outdir", type=Path, default=Path.home() / ".agents/prds")
    parser.add_argument("--include-bots", action="store_true")
    parser.add_argument(
        "--strict-bots",
        action="store_true",
        help="also skip authors matching the broad automation regex",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--list-attachments",
        action="store_true",
        help="print attachment id/filename/outputPath JSON and exit (no PRD write)",
    )
    args = parser.parse_args()

    if args.list_attachments:
        if args.batch:
            parser.error("--list-attachments does not support --batch")
        raw = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        payload = json.loads(raw)
        issue = find_issue(payload)
        if not issue:
            raise ValueError("could not find a Jira issue object")
        fields = issue.get("fields") or issue
        key = str(issue.get("key") or fields.get("key") or "UNKNOWN")
        files = list_attachments(fields, key)
        listing = {
            "key": key,
            "dir": str(attachments_dir(key)),
            "attachments": files,
        }
        print(json.dumps(listing, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    results = []
    if args.batch:
        for path in args.batch:
            payload = json.loads(path.read_text(encoding="utf-8"))
            key, _, _ = render(payload, args.include_bots, args.strict_bots)
            results.append(write(payload, args.outdir / f"{key}.md", args))
    else:
        if not args.output:
            parser.error("--output is required unless --batch is used")
        raw = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        results.append(write(json.loads(raw), args.output, args))

    if args.json:
        payload_out = results if args.batch else results[0]
        print(json.dumps(payload_out, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        for result in results:
            print(result["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
