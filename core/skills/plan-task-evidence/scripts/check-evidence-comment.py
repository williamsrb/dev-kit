#!/usr/bin/env python3
"""Lint a Jira evidence-comment body before it is posted.

Enforces the rules in ``templates.md`` § "Jira evidence comment" that are
mechanically checkable, so a malformed comment fails here instead of in the
analyst's inbox. It fails on gallery dumps, orphaned or thinly-captioned images,
percentage-sized media figures (PROJ-435 letterbox), figures missing PNG
pixel width/height, leaked local paths, evidence-machine logistics, missing
sections, analyst questions, and env-root URLs with no page path.

Usage:
    check-evidence-comment.py BODY.html [--format html|markdown]
    cat body.html | check-evidence-comment.py -

Exit codes: 0 = clean, 1 = violations found, 2 = bad invocation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# Paths that must never reach a Jira comment.
LOCAL_PATH_RE = re.compile(
    r"(~/|/home/|/Users/|/tmp/|[A-Za-z]:\\|\.\./|\bfile://)"
)
# Evidence-machine logistics the analyst must never read about.
LOGISTICS_RE = re.compile(
    r"\b(mogrify|imagemagick|playwright|storage[- ]state|screenshot folder"
    r"|please attach|upload(ed)? (the )?attachment|evidence folder"
    r"|local report|agentctl|headless|browser mcp)\b",
    re.IGNORECASE,
)
# Praise / thanks aimed at the analyst. They are doing their job; grading it is
# condescending and has been called out by a reporter. See write-analyst-message.
PRAISE_RE = re.compile(
    r"(thanks?\s+(you\s+)?for\b|thank you\b|thanks!|good (catch|call|point|spot)"
    r"|nice (catch|call|spot)|well spotted|you('re| are| were) (right|correct)"
    r"|(was|were) the right call|right call\b|great (question|point|catch)"
    r"|appreciate (your|the)|correct to (flag|report|raise)"
    r"|(sharp|excellent|good) (eye|observation)|spot on\b)",
    re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"\[Attachment:\s*([^\]]+)\]")

# Evidence comments are verification, not a decision request. Option lists belong
# in a separate TBD comment. See plan-task-evidence skill override 5.
QUESTION_RE = re.compile(
    r"(my recommendation|"
    r"without an answer we get|"
    r"a letter (on|for|is enough)|"
    r"which (would you|do you) (like|want|prefer)|"
    r"pick (option )?\(?[abc]\)|"
    r"<strong>\s*a\)|"
    r"\*\*\s*a\)|"
    r"recommended option|"
    r"2-3 options)",
    re.IGNORECASE,
)

# Review/staging host with no page path — useless to the analyst. A live path or
# CS /admin/.../edit/<id> is required. See plan-task-evidence skill override 7.
#
# Which hosts those are is client-bound, so it is not hardcoded here (plan
# devkit, A0/B3). Patterns come from the client overlay config; with no
# config the check is skipped rather than guessed at, because a bare root URL
# is only a defect for an environment host.
HOST_CHAR = r"[^/\s\"'<>]"


def _client_overlay_path() -> Path:
    override = os.environ.get("AGENTS_CLIENT_OVERLAY")
    if override:
        return Path(override).expanduser()
    agents_home = os.environ.get("AGENTS_HOME")
    root = Path(agents_home).expanduser() if agents_home else Path.home() / ".agents"
    return root / "config" / "client-overlay.json"


def _load_env_root_re() -> re.Pattern[str] | None:
    """Build the env-root URL matcher from the client overlay, or None."""
    path = _client_overlay_path()
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    patterns = config.get("env_root_host_patterns") or []
    if not isinstance(patterns, list):
        return None
    alternatives = []
    for pattern in patterns:
        if not isinstance(pattern, str) or not pattern:
            continue
        alternatives.append(
            (HOST_CHAR + "*").join(re.escape(part) for part in pattern.split("*"))
        )
    if not alternatives:
        return None
    return re.compile(
        r"https?://" + HOST_CHAR + r"*?(?:" + "|".join(alternatives) + r")"
        r"/?(?=[\"'\s<]|$)",
        re.IGNORECASE,
    )


GENERIC_ENV_ROOT_RE = _load_env_root_re()

# Minimum prose (characters) that counts as a real explanation for an image.
MIN_EXPLANATION_CHARS = 40

# Desktop captures (~1440 after stamp) use layout wide. Tight clips stay center.
# Ground truth: PROJ-435 comment 531480 after the analyst UI save (2026-09-15).
WIDE_LAYOUT_MIN_PX = 1200.0

# Pasted Jira renderer HTML — not an authored fragment.
RENDERER_CHROME_RE = re.compile(
    r"ak-renderer-wrapper|new-file-experience-wrapper|media-card-view|"
    r"media-file-card-view|visually-hidden-heading-anchor",
    re.IGNORECASE,
)


class Node:
    """Flat document event: either prose text or a media figure."""

    __slots__ = ("kind", "text", "line", "attrs")

    def __init__(
        self,
        kind: str,
        text: str,
        line: int,
        attrs: dict[str, str] | None = None,
    ) -> None:
        self.kind = kind  # "text" | "figure" | "heading" | "table"
        self.text = text
        self.line = line
        self.attrs = attrs or {}


class BodyParser(HTMLParser):
    """Flattens the comment into an ordered list of prose / figure events."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nodes: list[Node] = []
        self.media_ids: list[str] = []
        self._figure_depth = 0
        self._heading_depth = 0
        self._ec_pending = ""
        self._ec_pending_line = 1

    def _flush(self) -> None:
        text = " ".join(self._ec_pending.split())
        if text:
            kind = "heading" if self._heading_depth else "text"
            self.nodes.append(Node(kind, text, self._ec_pending_line))
        self._ec_pending = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        if tag == "figure" or attr.get("data-type") == "media-single":
            self._flush()
            self._figure_depth += 1
            self.nodes.append(Node("figure", "", self.getpos()[0], attr))
        elif tag == "div" and attr.get("data-type") == "media":
            self.media_ids.append(attr.get("data-id", ""))
            if self._figure_depth and self.nodes and self.nodes[-1].kind == "figure":
                self.nodes[-1].attrs["media-width"] = attr.get("data-width", "")
                self.nodes[-1].attrs["media-height"] = attr.get("data-height", "")
        elif tag == "table":
            self._flush()
            self.nodes.append(Node("table", "", self.getpos()[0]))
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush()
            self._heading_depth += 1
            self._ec_pending_line = self.getpos()[0]
        elif tag in {"p", "li", "br"}:
            self._flush()
            self._ec_pending_line = self.getpos()[0]

    def handle_endtag(self, tag: str) -> None:
        if tag == "figure" and self._figure_depth:
            self._figure_depth -= 1
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush()
            if self._heading_depth:
                self._heading_depth -= 1
        elif tag in {"p", "li"}:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._figure_depth:
            # Text inside a <figure> (filename, caption) is not an explanation.
            return
        if not self._ec_pending.strip():
            self._ec_pending_line = self.getpos()[0]
        self._ec_pending += data

    def close(self) -> None:  # noqa: D102
        super().close()
        self._flush()


def check_html(body: str) -> list[str]:
    parser = BodyParser()
    parser.feed(body)
    parser.close()
    problems: list[str] = []

    figures = [n for n in parser.nodes if n.kind == "figure"]
    if not figures and not PLACEHOLDER_RE.search(body):
        problems.append(
            "No media figures and no [Attachment: ...] placeholders — an evidence "
            "comment must carry the evidence."
        )

    # Rule: every figure sits immediately under its own explanation.
    for index, node in enumerate(parser.nodes):
        if node.kind != "figure":
            continue
        previous = parser.nodes[index - 1] if index else None
        if previous is None:
            problems.append(
                f"line {node.line}: figure opens the comment with no explanation above it."
            )
        elif previous.kind == "figure":
            problems.append(
                f"line {node.line}: two figures back to back — this is a gallery dump. "
                "Each image needs its own explanation of what it proves."
            )
        elif previous.kind == "heading":
            problems.append(
                f"line {node.line}: figure sits directly under a heading. A heading is not "
                "an explanation; state what the image proves toward an AC."
            )
        elif previous.kind == "table":
            problems.append(
                f"line {node.line}: figure sits directly under a table."
            )
        elif len(previous.text) < MIN_EXPLANATION_CHARS:
            problems.append(
                f"line {node.line}: explanation above the figure is only "
                f"{len(previous.text)} chars ({previous.text!r}) — too thin to give the "
                "image meaning."
            )

    # Rule: an uploaded file is embedded, never referenced as a placeholder.
    if parser.media_ids and PLACEHOLDER_RE.search(body):
        problems.append(
            "Body mixes embedded media nodes with [Attachment: ...] placeholders — "
            "placeholders are only for files whose upload failed."
        )

    problems.extend(check_figure_sizing(parser.nodes, body))
    problems.extend(check_common(body))
    return problems


def check_figure_sizing(nodes: list[Node], body: str) -> list[str]:
    """Require PNG pixel sizing. 60% figures letterbox (PROJ-435)."""
    problems: list[str] = []
    if RENDERER_CHROME_RE.search(body):
        problems.append(
            "Body looks like Jira's rendered comment HTML (ak-renderer / media-card "
            "wrappers). Author the fragment from templates.md — one <figure> wrapping "
            "one media <div> with data-width/data-height from identify. Jira adds the rest."
        )
    for node in nodes:
        if node.kind != "figure":
            continue
        width_type = (node.attrs.get("data-width-type") or "").strip().lower()
        width_raw = (node.attrs.get("data-width") or "").strip()
        layout = (node.attrs.get("data-layout") or "").strip().lower()
        media_w_raw = (node.attrs.get("media-width") or "").strip()
        media_h_raw = (node.attrs.get("media-height") or "").strip()
        if width_type == "percentage":
            problems.append(
                f"line {node.line}: data-width-type=\"percentage\" letterboxes the "
                "image (Jira reserves a 250×200-aspect box). Use data-width-type="
                "\"pixel\", data-width from identify, and inner data-width/data-height "
                "(PROJ-435 comment 531480)."
            )
            continue
        if width_type != "pixel":
            problems.append(
                f"line {node.line}: figure needs data-width-type=\"pixel\" and "
                "data-width set to the PNG pixel width from identify."
            )
            continue
        try:
            width = float(width_raw)
        except ValueError:
            problems.append(
                f"line {node.line}: data-width={width_raw!r} is not a pixel number."
            )
            continue
        if width <= 0:
            problems.append(
                f"line {node.line}: data-width={width_raw} must be the PNG pixel width."
            )
            continue
        try:
            media_w = float(media_w_raw) if media_w_raw else 0.0
            media_h = float(media_h_raw) if media_h_raw else 0.0
        except ValueError:
            media_w = media_h = 0.0
        if media_w <= 0 or media_h <= 0:
            problems.append(
                f"line {node.line}: inner media div needs data-width and data-height "
                "from identify of the flattened PNG. Without them Jira letterboxes."
            )
            continue
        if abs(media_w - width) > 0.5:
            problems.append(
                f"line {node.line}: figure data-width={width_raw} must match inner "
                f"data-width={media_w_raw} (PNG width)."
            )
        expect_wide = width >= WIDE_LAYOUT_MIN_PX
        if expect_wide and layout != "wide":
            problems.append(
                f"line {node.line}: PNG width {width_raw}px needs data-layout=\"wide\" "
                "(desktop capture). data-layout={layout!r} letterboxes or shrinks it."
            )
        if not expect_wide and layout == "wide":
            problems.append(
                f"line {node.line}: PNG width {width_raw}px is a clip — use "
                "data-layout=\"center\", not wide."
            )
    return problems


def check_markdown(body: str) -> list[str]:
    problems: list[str] = []
    lines = body.splitlines()
    placeholders = [i for i, line in enumerate(lines) if PLACEHOLDER_RE.search(line)]
    if not placeholders:
        problems.append("No [Attachment: ...] placeholders found in a markdown body.")
    for index in placeholders:
        preceding = ""
        cursor = index
        # Allow the placeholder to trail its explanation on the same line.
        same_line = PLACEHOLDER_RE.sub("", lines[index]).strip(" \t-*0123456789.")
        if len(same_line) >= MIN_EXPLANATION_CHARS:
            continue
        while cursor > 0 and not preceding:
            cursor -= 1
            candidate = lines[cursor].strip()
            if PLACEHOLDER_RE.search(candidate):
                problems.append(
                    f"line {index + 1}: two placeholders back to back — gallery dump."
                )
                break
            preceding = candidate.strip(" \t-*0123456789.")
        else:
            if len(preceding) < MIN_EXPLANATION_CHARS:
                problems.append(
                    f"line {index + 1}: placeholder has no real explanation above it."
                )
    problems.extend(check_common(body))
    return problems


def check_common(body: str) -> list[str]:
    problems: list[str] = []
    for match in LOCAL_PATH_RE.finditer(body):
        snippet = body[max(0, match.start() - 30) : match.end() + 30]
        problems.append(
            f"Local path leaked into the comment near: {' '.join(snippet.split())!r}"
        )
    for match in LOGISTICS_RE.finditer(body):
        snippet = body[max(0, match.start() - 40) : match.end() + 40]
        problems.append(
            f"Evidence-machine logistics ({match.group(0)!r}) — analyst-facing bodies keep "
            f"this in the chat report: {' '.join(snippet.split())!r}"
        )
    for match in PRAISE_RE.finditer(body):
        snippet = body[max(0, match.start() - 40) : match.end() + 40]
        problems.append(
            f"Praise/thanks aimed at the analyst ({match.group(0)!r}) — never thank, praise, "
            f"or grade their work; state the finding instead: {' '.join(snippet.split())!r}"
        )
    for match in QUESTION_RE.finditer(body):
        snippet = body[max(0, match.start() - 40) : match.end() + 40]
        problems.append(
            f"Analyst question in an evidence comment ({match.group(0)!r}) — E2 does not ask; "
            f"state the shipped fact or park the decision in chat / a separate TBD comment: "
            f"{' '.join(snippet.split())!r}"
        )
    seen_roots: set[str] = set()
    if GENERIC_ENV_ROOT_RE is not None:
        for match in GENERIC_ENV_ROOT_RE.finditer(body):
            url = match.group(0)
            if url in seen_roots:
                continue
            seen_roots.add(url)
            problems.append(
                "Env-root URL with no page path "
                f"({url!r}) — link the captured live page and Admin CS edit URL, "
                "not the environment root."
            )
    lowered = body.lower()
    if "changes summary" not in lowered:
        problems.append("Missing the 'Changes summary' section.")
    if not re.search(r"acceptance criteri", lowered):
        problems.append("Missing the 'Acceptance criteria' section.")
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("body", help="path to the comment body, or - for stdin")
    parser.add_argument(
        "--format",
        choices=("html", "markdown"),
        default="html",
        help="body format (default: html)",
    )
    args = parser.parse_args(argv)

    if args.body == "-":
        text = sys.stdin.read()
    else:
        path = Path(args.body).expanduser()
        if not path.is_file():
            print(f"error: no such file: {path}", file=sys.stderr)
            return 2
        text = path.read_text(encoding="utf-8")

    problems = check_html(text) if args.format == "html" else check_markdown(text)

    if problems:
        print(f"BLOCKED — {len(problems)} violation(s); do not post this comment:\n")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "\nFix against templates.md § 'Jira evidence comment', then re-run this check."
        )
        return 1

    print("OK — evidence comment body passes the format gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
