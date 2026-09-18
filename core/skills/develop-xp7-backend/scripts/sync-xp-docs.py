#!/usr/bin/env python3
"""Sync Enonic XP 7.x docs to LLM-dense offline markdown."""
from __future__ import annotations

from pathlib import Path

import argparse
import datetime as dt
import html as html_lib
import os
import re
import sys
import urllib.error
import urllib.request

DOC_BASE = "https://developer.enonic.com/docs/platform/7.x"

URL_GROUPS = {
    "development": [
        ("development", f"{DOC_BASE}/development"),
        ("sandboxes", f"{DOC_BASE}/development/sandboxes"),
        ("code", f"{DOC_BASE}/development/code"),
        ("build", f"{DOC_BASE}/development/build"),
        ("config", f"{DOC_BASE}/development/config"),
        ("typescript", f"{DOC_BASE}/development/typescript"),
    ],
    "framework": [
        ("framework", f"{DOC_BASE}/framework"),
        ("controllers", f"{DOC_BASE}/framework/controllers"),
        ("globals", f"{DOC_BASE}/framework/globals"),
        ("http", f"{DOC_BASE}/framework/http"),
        ("events", f"{DOC_BASE}/framework/events"),
        ("error", f"{DOC_BASE}/framework/error"),
        ("filters", f"{DOC_BASE}/framework/filters"),
        ("idprovider", f"{DOC_BASE}/framework/idprovider"),
        ("tasks", f"{DOC_BASE}/framework/tasks"),
        ("templating", f"{DOC_BASE}/framework/templating"),
        ("i18n", f"{DOC_BASE}/framework/i18n"),
        ("websocket", f"{DOC_BASE}/framework/websocket"),
        ("mappings", f"{DOC_BASE}/framework/mappings"),
        ("components", f"{DOC_BASE}/framework/components"),
        ("processors", f"{DOC_BASE}/framework/processors"),
        ("contributions", f"{DOC_BASE}/framework/contributions"),
        ("main", f"{DOC_BASE}/framework/main"),
        ("java-bridge", f"{DOC_BASE}/framework/java-bridge"),
    ],
    "api": [
        ("api", f"{DOC_BASE}/api"),
        ("lib-admin", f"{DOC_BASE}/api/lib-admin"),
        ("lib-app", f"{DOC_BASE}/api/lib-app"),
        ("lib-auditlog", f"{DOC_BASE}/api/lib-auditlog"),
        ("lib-auth", f"{DOC_BASE}/api/lib-auth"),
        ("lib-cluster", f"{DOC_BASE}/api/lib-cluster"),
        ("lib-common", f"{DOC_BASE}/api/lib-common"),
        ("lib-content", f"{DOC_BASE}/api/lib-content"),
        ("lib-context", f"{DOC_BASE}/api/lib-context"),
        ("lib-event", f"{DOC_BASE}/api/lib-event"),
        ("lib-export", f"{DOC_BASE}/api/lib-export"),
        ("lib-grid", f"{DOC_BASE}/api/lib-grid"),
        ("lib-i18n", f"{DOC_BASE}/api/lib-i18n"),
        ("lib-io", f"{DOC_BASE}/api/lib-io"),
        ("lib-mail", f"{DOC_BASE}/api/lib-mail"),
        ("lib-node", f"{DOC_BASE}/api/lib-node"),
        ("lib-portal", f"{DOC_BASE}/api/lib-portal"),
        ("lib-project", f"{DOC_BASE}/api/lib-project"),
        ("lib-repo", f"{DOC_BASE}/api/lib-repo"),
        ("lib-scheduler", f"{DOC_BASE}/api/lib-scheduler"),
        ("lib-schema", f"{DOC_BASE}/api/lib-schema"),
        ("lib-task", f"{DOC_BASE}/api/lib-task"),
        ("lib-value", f"{DOC_BASE}/api/lib-value"),
        ("lib-vhost", f"{DOC_BASE}/api/lib-vhost"),
        ("lib-websocket", f"{DOC_BASE}/api/lib-websocket"),
    ],
}

ANY_DIV_RE = re.compile(r"</?div\b[^>]*>", re.I)
TAG_RE = re.compile(r"(?is)<[^>]+>")
WS_RE = re.compile(r"[ \t]+\n")
MULTI_NL_RE = re.compile(r"\n{3,}")
HEADING_LINK_RE = re.compile(r'(?is)<a\b[^>]*class="[^"]*link[^"]*"[^>]*>(.*?)</a>')
VERSION_BADGE_RE = re.compile(
    r"(?i)\bXP\s*XP\s*7\.\d+(?:\.\d+)?\s*7\.\d+(?:\.\d+)?\b|\bXP\s+7\.\d+(?:\.\d+)?\s+7\.\d+(?:\.\d+)?\b"
)
IMAGE_SVG_RE = re.compile(r'(?is)<span\b[^>]*class="[^"]*\bimage\b[^"]*"[^>]*>.*?</span>')
ADMONITION_RE = re.compile(
    r'(?is)<div\b[^>]*class="[^"]*\badmonitionblock\s+(\w+)[^"]*"[^>]*>.*?</table>\s*</div>'
)


def fetch_html(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; enonic-xp-doc-sync/2.0)",
            "Accept": "text/html",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_balanced_div(html_text: str, *, div_id: str | None = None, class_name: str | None = None) -> str | None:
    if div_id:
        open_re = re.compile(rf'<div\b[^>]*\bid=["\']{re.escape(div_id)}["\'][^>]*>', re.I)
    elif class_name:
        open_re = re.compile(
            rf'<div\b[^>]*\bclass=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'][^>]*>',
            re.I,
        )
    else:
        return None

    m = open_re.search(html_text)
    if not m:
        return None

    start = m.end()
    depth = 1
    i = start
    while depth and i < len(html_text):
        tm = ANY_DIV_RE.search(html_text, i)
        if not tm:
            break
        token = tm.group(0)
        if token.lower().startswith("</"):
            depth -= 1
            if depth == 0:
                return html_text[start : tm.start()]
        elif not token.rstrip().endswith("/>"):
            depth += 1
        i = tm.end()
    return None


def extract_title(html_text: str) -> str:
    m = re.search(
        r'<div class="docpage-content__title">\s*<h1[^>]*>(.*?)</h1>',
        html_text,
        flags=re.I | re.S,
    )
    if m:
        return normalize_inline(m.group(1))
    m = re.search(r"<title>(.*?)</title>", html_text, flags=re.I | re.S)
    if not m:
        return "Untitled"
    title = html_lib.unescape(re.sub(r"\s+", " ", m.group(1)).strip())
    title = re.sub(r"\s*-\s*Enonic.*$", "", title).strip()
    return title or "Untitled"


def strip_tags(text: str) -> str:
    return TAG_RE.sub("", text)


def normalize_inline(text: str) -> str:
    text = HEADING_LINK_RE.sub(r"\1", text)
    text = re.sub(r"(?is)<code\b[^>]*>(.*?)</code>", r"`\1`", text)
    text = re.sub(r"(?is)<(?:strong|b)\b[^>]*>(.*?)</(?:strong|b)>", r"**\1**", text)
    text = re.sub(r"(?is)<(?:em|i)\b[^>]*>(.*?)</(?:em|i)>", r"*\1*", text)
    text = re.sub(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r"[\2](\1)", text)
    text = strip_tags(text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = VERSION_BADGE_RE.sub("", text)
    return text.strip()


def cell_text(cell_html: str) -> str:
    text = normalize_inline(cell_html)
    return text.replace("|", "\\|").replace("\n", " ")


def convert_table(table_html: str) -> str:
    rows = []
    for tr in re.finditer(r"(?is)<tr\b[^>]*>(.*?)</tr>", table_html):
        cells = re.findall(r"(?is)<t[hd]\b[^>]*>(.*?)</t[hd]>", tr.group(1))
        if cells:
            rows.append([cell_text(c) for c in cells])
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    for r in rows:
        while len(r) < width:
            r.append("")
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else []
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for r in body:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines) + "\n\n"


def convert_pre(pre_html: str) -> str:
    lang = ""
    m = re.search(r'(?is)<code\b[^>]*data-lang=["\']([^"\']+)["\']', pre_html)
    if not m:
        m = re.search(r'(?is)<code\b[^>]*class=["\'][^"\']*language-([a-z0-9_+-]+)', pre_html)
    if m:
        lang = m.group(1).strip()
    code = strip_tags(pre_html)
    code = html_lib.unescape(code).replace("\r", "")
    code = re.sub(r"\n+\Z", "\n", code)
    if not code.endswith("\n"):
        code += "\n"
    return f"```{lang}\n{code}```\n\n"


def svg_version_label(svg_or_image_html: str) -> str:
    texts = [html_lib.unescape(t).strip() for t in re.findall(r"(?is)<text\b[^>]*>(.*?)</text>", svg_or_image_html)]
    texts = [t for t in texts if t]
    # Badge SVGs duplicate each label (shadow + fill); unique in order.
    uniq: list[str] = []
    for t in texts:
        if not uniq or uniq[-1] != t:
            uniq.append(t)
    if not uniq:
        return ""
    return " ".join(uniq)


def replace_version_images(html_fragment: str) -> str:
    def repl(m: re.Match) -> str:
        label = svg_version_label(m.group(0))
        return label or ""

    return IMAGE_SVG_RE.sub(repl, html_fragment)


def convert_admonition(kind: str, block_html: str) -> str:
    content_m = re.search(r'(?is)<td\b[^>]*class="[^"]*\bcontent\b[^"]*"[^>]*>(.*?)</td>', block_html)
    body = content_m.group(1) if content_m else block_html
    body = replace_version_images(body)
    body = normalize_inline(body)
    if not body:
        return ""
    label = kind.capitalize()
    return f"> **{label}:** {body}\n\n"


def dedent_outside_fences(text: str) -> str:
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        out.append(line if in_fence else line.lstrip(" \t"))
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def html_to_llm_markdown(fragment: str) -> str:
    s = fragment
    s = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", "", s)
    s = re.sub(r'(?is)<div\b[^>]*class="[^"]*docpage-toc[^"]*"[^>]*>.*?</div>', "", s)
    s = replace_version_images(s)

    # Protect blocks that need structure-preserving conversion.
    blocks: list[str] = []

    def stash(value: str) -> str:
        blocks.append(value)
        return f"\n@@BLOCK{len(blocks) - 1}@@\n"

    def stash_admonition(m: re.Match) -> str:
        return stash(convert_admonition(m.group(1), m.group(0)))

    def stash_table(m: re.Match) -> str:
        return stash(convert_table(m.group(0)))

    def stash_pre(m: re.Match) -> str:
        return stash(convert_pre(m.group(0)))

    s = ADMONITION_RE.sub(stash_admonition, s)
    s = re.sub(r"(?is)<table\b[^>]*>.*?</table>", stash_table, s)
    s = re.sub(r"(?is)<pre\b[^>]*>.*?</pre>", stash_pre, s)

    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(
        r"(?is)<h1\b[^>]*>(.*?)</h1>",
        lambda m: "\n# " + normalize_inline(m.group(1)) + "\n\n",
        s,
    )
    s = re.sub(
        r"(?is)<h2\b[^>]*>(.*?)</h2>",
        lambda m: "\n## " + normalize_inline(m.group(1)) + "\n\n",
        s,
    )
    s = re.sub(
        r"(?is)<h3\b[^>]*>(.*?)</h3>",
        lambda m: "\n### " + normalize_inline(m.group(1)) + "\n\n",
        s,
    )
    s = re.sub(
        r"(?is)<h4\b[^>]*>(.*?)</h4>",
        lambda m: "\n#### " + normalize_inline(m.group(1)) + "\n\n",
        s,
    )
    s = re.sub(
        r"(?is)<li\b[^>]*>(.*?)</li>",
        lambda m: "- " + normalize_inline(m.group(1)) + "\n",
        s,
    )
    s = re.sub(
        r"(?is)<p\b[^>]*>(.*?)</p>",
        lambda m: normalize_inline(m.group(1)) + "\n\n",
        s,
    )
    s = re.sub(r"(?is)</?(?:ul|ol|div|span|section|article|header|footer|nav|aside|main)[^>]*>", "\n", s)
    s = strip_tags(s)
    s = html_lib.unescape(s)

    for i, block in enumerate(blocks):
        s = s.replace(f"@@BLOCK{i}@@", "\n" + block)

    s = s.replace("\r", "")
    s = VERSION_BADGE_RE.sub("", s)
    s = WS_RE.sub("\n", s)
    s = MULTI_NL_RE.sub("\n\n", s)
    s = dedent_outside_fences(s)
    # Drop leftover empty list markers / chrome crumbs.
    s = re.sub(r"(?m)^-\s*$", "", s)
    s = MULTI_NL_RE.sub("\n\n", s)
    return s.strip() + "\n"


def token_line(group: str, slug: str, title: str, body: str) -> str:
    parts = [group, slug.replace("-", " "), title.lower()]
    # Prefer API function headings and framework keywords for search routing.
    heads = re.findall(r"(?m)^#{2,4}\s+(.+)$", body)
    parts.extend(h.lower() for h in heads[:24])
    text = " ".join(parts)
    text = re.sub(r"[^a-z0-9_./+\- ]+", " ", text.lower())
    tokens = []
    seen = set()
    for tok in text.split():
        if tok in seen or len(tok) < 2:
            continue
        seen.add(tok)
        tokens.append(tok)
        if len(tokens) >= 40:
            break
    return " ".join(tokens)


def write_page(output_dir: str, group: str, slug: str, url: str, generated_at: str) -> tuple[str, str]:
    group_dir = os.path.join(output_dir, group)
    os.makedirs(group_dir, exist_ok=True)
    rel = f"{group}/{slug}.md"
    path = os.path.join(output_dir, rel)

    html_text = fetch_html(url)
    title = extract_title(html_text)
    content = extract_balanced_div(html_text, div_id="content")
    if not content:
        content = extract_balanced_div(html_text, class_name="docpage-content__doc") or html_text
    body = html_to_llm_markdown(content)

    # Avoid duplicate H1 if converter kept one.
    body_wo_dup = re.sub(rf"(?im)^#\s+{re.escape(title)}\s*\n+", "", body, count=1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!-- src:{url} generated:{generated_at} format:llm-dense xp:7.x -->\n")
        f.write(f"#DOC {rel}\n\n")
        f.write(f"# {title}\n\n")
        f.write(body_wo_dup if body_wo_dup.strip() else body)

    return rel, token_line(group, slug, title, body_wo_dup)


def write_index(output_dir: str, generated_at: str, rows: list[tuple[str, str, str]]) -> None:
    index_path = os.path.join(output_dir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# Enonic XP 7.x Offline Docs Index\n\n")
        f.write(f"Generated: {generated_at}\n")
        f.write("Format: llm-dense\n")
        f.write(f"Source base: {DOC_BASE}\n\n")
        f.write("| Group | Page | File | URL |\n")
        f.write("| --- | --- | --- | --- |\n")
        for group, slug, url in rows:
            rel = f"{group}/{slug}.md"
            f.write(f"| {group} | {slug} | `{rel}` | {url} |\n")


def write_llm_index(output_dir: str, entries: list[tuple[str, str]]) -> None:
    path = os.path.join(output_dir, "llm-index.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# LLM_INDEX|machine|v1|path<TAB>tokens\n\n")
        for rel, tokens in entries:
            f.write(f"{rel}\t{tokens}\n")


def main() -> int:
    _script_dir = Path(__file__).resolve().parent
    default_output = str((_script_dir / "../../../kb/offline-reference/xp7").resolve())
    parser = argparse.ArgumentParser(description="Sync Enonic XP 7.x docs to LLM-dense markdown.")
    parser.add_argument(
        "--output",
        default=default_output,
        help="Output folder (default: ~/.agents/kb/offline-reference/xp7)",
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output)
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    rows: list[tuple[str, str, str]] = []
    llm_entries: list[tuple[str, str]] = []
    failures: list[tuple[str, str, str, str]] = []

    for group, items in URL_GROUPS.items():
        for slug, url in items:
            try:
                rel, tokens = write_page(output_dir, group, slug, url, generated_at)
                rows.append((group, slug, url))
                llm_entries.append((rel, tokens))
                print(f"[OK] {rel}")
            except urllib.error.URLError as e:
                failures.append((group, slug, url, f"URLError: {e}"))
                print(f"[ERR] {group}/{slug} -> {e}", file=sys.stderr)
            except Exception as e:  # noqa: BLE001
                failures.append((group, slug, url, f"Error: {e}"))
                print(f"[ERR] {group}/{slug} -> {e}", file=sys.stderr)

    write_index(output_dir, generated_at, rows)
    write_llm_index(output_dir, llm_entries)

    if failures:
        print("\nSome pages failed to sync:", file=sys.stderr)
        for group, slug, url, err in failures:
            print(f"- {group}/{slug}: {url} ({err})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
