#!/usr/bin/env python3
"""Cascade-sync Enonic React4XP docs to LLM-dense offline markdown.

Example:
  sync-react4xp-docs.py \\
    --seed https://developer.enonic.com/learn/react4xp-tutorial/5.x \\
    --prefix /learn/react4xp-tutorial/5.x \\
    --tag react4xp-5.x \\
    --output ~/.agents/kb/offline-reference/react4xp-5.x

In-scope links rewrite to learn/react4xp-tutorial/<channel>/....md (shared learn/* base).
"""
from __future__ import annotations

from pathlib import Path

import argparse
import datetime as dt
import html as html_lib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse

HOST = "https://developer.enonic.com"

ASSET_EXTS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".css",
    ".js",
    ".mjs",
    ".map",
    ".pdf",
    ".zip",
    ".tgz",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".ahtml",
)

ANY_DIV_RE = re.compile(r"</?div\b[^>]*>", re.I)
TAG_RE = re.compile(r"(?is)<[^>]+>")
WS_RE = re.compile(r"[ \t]+\n")
MULTI_NL_RE = re.compile(r"\n{3,}")
HEADING_LINK_RE = re.compile(r'(?is)<a\b[^>]*class="[^"]*link[^"]*"[^>]*>(.*?)</a>')
HREF_RE = re.compile(r"""href=["']([^"']+)["']""", re.I)
VERSION_BADGE_RE = re.compile(
    r"(?i)\bXP\s*XP\s*[78]\.\d+(?:\.\d+)?\s*[78]\.\d+(?:\.\d+)?\b|"
    r"\bXP\s+[78]\.\d+(?:\.\d+)?\s+[78]\.\d+(?:\.\d+)?\b"
)
IMAGE_SVG_RE = re.compile(r'(?is)<span\b[^>]*class="[^"]*\bimage\b[^"]*"[^>]*>.*?</span>')
ADMONITION_RE = re.compile(
    r'(?is)<div\b[^>]*class="[^"]*\badmonitionblock\s+(\w+)[^"]*"[^>]*>.*?</table>\s*</div>'
)

# Filled in main()
PATH_PREFIXES: tuple[str, ...] = ()
START_URLS: list[str] = []
DOC_TAG = "react4xp"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def path_allowed(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in PATH_PREFIXES)


def is_junk_path(path: str) -> bool:
    if "${" in path or "{" in path or "}" in path:
        return True
    lower = path.lower()
    return any(lower.endswith(ext) for ext in ASSET_EXTS)


def normalize_doc_url(url: str, base: str | None = None) -> str | None:
    if base:
        url = urljoin(base, url)
    url, _frag = urldefrag(url)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", ""):
        return None
    if parsed.netloc and parsed.netloc != "developer.enonic.com":
        return None
    path = parsed.path.rstrip("/") or "/"
    if not path_allowed(path) or is_junk_path(path):
        return None
    return HOST + path


def url_to_rel_md(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.lstrip("/") + ".md"


def rewrite_href_for_offline(href: str, page_url: str) -> str:
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "javascript:")):
        return href

    abs_url = urljoin(page_url, href)
    parsed = urlparse(abs_url)
    frag = ("#" + parsed.fragment) if parsed.fragment else ""
    clean = urldefrag(abs_url)[0]
    norm = normalize_doc_url(clean)
    if norm:
        return url_to_rel_md(norm) + frag

    if parsed.scheme in ("http", "https"):
        return clean + frag
    return href


def fetch_html(url: str, timeout: int = 30) -> tuple[str, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; enonic-react4xp-doc-sync/1.0)",
            "Accept": "text/html",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace"), resp.geturl()


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


def strip_tags(text: str) -> str:
    return TAG_RE.sub("", text)


def normalize_inline(text: str, page_url: str) -> str:
    text = HEADING_LINK_RE.sub(r"\1", text)
    text = re.sub(r"(?is)<code\b[^>]*>(.*?)</code>", r"`\1`", text)
    text = re.sub(r"(?is)<(?:strong|b)\b[^>]*>(.*?)</(?:strong|b)>", r"**\1**", text)
    text = re.sub(r"(?is)<(?:em|i)\b[^>]*>(.*?)</(?:em|i)>", r"*\1*", text)

    def link_repl(m: re.Match) -> str:
        href = rewrite_href_for_offline(m.group(1), page_url)
        label = html_lib.unescape(strip_tags(m.group(2))).strip()
        return f"[{label}]({href})"

    text = re.sub(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', link_repl, text)
    text = strip_tags(text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = VERSION_BADGE_RE.sub("", text)
    return text.strip()


def extract_title(html_text: str, page_url: str) -> str:
    m = re.search(
        r'<div class="docpage-content__title">\s*<h1[^>]*>(.*?)</h1>',
        html_text,
        flags=re.I | re.S,
    )
    if m:
        return normalize_inline(m.group(1), page_url)
    m = re.search(r"<title>(.*?)</title>", html_text, flags=re.I | re.S)
    if not m:
        return "Untitled"
    title = html_lib.unescape(re.sub(r"\s+", " ", m.group(1)).strip())
    title = re.sub(r"\s*-\s*Enonic.*$", "", title).strip()
    return title or "Untitled"


def cell_text(cell_html: str, page_url: str) -> str:
    return normalize_inline(cell_html, page_url).replace("|", "\\|").replace("\n", " ")


def convert_table(table_html: str, page_url: str) -> str:
    rows = []
    for tr in re.finditer(r"(?is)<tr\b[^>]*>(.*?)</tr>", table_html):
        cells = re.findall(r"(?is)<t[hd]\b[^>]*>(.*?)</t[hd]>", tr.group(1))
        if cells:
            rows.append([cell_text(c, page_url) for c in cells])
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    for r in rows:
        while len(r) < width:
            r.append("")
    header, body = rows[0], rows[1:]
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
    code = html_lib.unescape(strip_tags(pre_html)).replace("\r", "")
    code = re.sub(r"\n+\Z", "\n", code)
    if not code.endswith("\n"):
        code += "\n"
    return f"```{lang}\n{code}```\n\n"


def svg_version_label(svg_or_image_html: str) -> str:
    texts = [html_lib.unescape(t).strip() for t in re.findall(r"(?is)<text\b[^>]*>(.*?)</text>", svg_or_image_html)]
    texts = [t for t in texts if t]
    uniq: list[str] = []
    for t in texts:
        if not uniq or uniq[-1] != t:
            uniq.append(t)
    return " ".join(uniq) if uniq else ""


def replace_version_images(html_fragment: str) -> str:
    return IMAGE_SVG_RE.sub(lambda m: svg_version_label(m.group(0)) or "", html_fragment)


def convert_admonition(kind: str, block_html: str, page_url: str) -> str:
    content_m = re.search(r'(?is)<td\b[^>]*class="[^"]*\bcontent\b[^"]*"[^>]*>(.*?)</td>', block_html)
    body = content_m.group(1) if content_m else block_html
    body = normalize_inline(replace_version_images(body), page_url)
    if not body:
        return ""
    return f"> **{kind.capitalize()}:** {body}\n\n"


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


def html_to_llm_markdown(fragment: str, page_url: str) -> str:
    s = fragment
    s = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", "", s)
    s = re.sub(r'(?is)<div\b[^>]*class="[^"]*docpage-toc[^"]*"[^>]*>.*?</div>', "", s)
    s = replace_version_images(s)

    blocks: list[str] = []

    def stash(value: str) -> str:
        blocks.append(value)
        return f"\n@@BLOCK{len(blocks) - 1}@@\n"

    s = ADMONITION_RE.sub(lambda m: stash(convert_admonition(m.group(1), m.group(0), page_url)), s)
    s = re.sub(r"(?is)<table\b[^>]*>.*?</table>", lambda m: stash(convert_table(m.group(0), page_url)), s)
    s = re.sub(r"(?is)<pre\b[^>]*>.*?</pre>", lambda m: stash(convert_pre(m.group(0))), s)

    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?is)<h1\b[^>]*>(.*?)</h1>", lambda m: "\n# " + normalize_inline(m.group(1), page_url) + "\n\n", s)
    s = re.sub(r"(?is)<h2\b[^>]*>(.*?)</h2>", lambda m: "\n## " + normalize_inline(m.group(1), page_url) + "\n\n", s)
    s = re.sub(r"(?is)<h3\b[^>]*>(.*?)</h3>", lambda m: "\n### " + normalize_inline(m.group(1), page_url) + "\n\n", s)
    s = re.sub(r"(?is)<h4\b[^>]*>(.*?)</h4>", lambda m: "\n#### " + normalize_inline(m.group(1), page_url) + "\n\n", s)
    s = re.sub(r"(?is)<li\b[^>]*>(.*?)</li>", lambda m: "- " + normalize_inline(m.group(1), page_url) + "\n", s)
    s = re.sub(r"(?is)<p\b[^>]*>(.*?)</p>", lambda m: normalize_inline(m.group(1), page_url) + "\n\n", s)
    s = re.sub(r"(?is)</?(?:ul|ol|div|span|section|article|header|footer|nav|aside|main)[^>]*>", "\n", s)
    s = html_lib.unescape(strip_tags(s))

    for i, block in enumerate(blocks):
        s = s.replace(f"@@BLOCK{i}@@", "\n" + block)

    s = VERSION_BADGE_RE.sub("", s.replace("\r", ""))
    s = WS_RE.sub("\n", s)
    s = MULTI_NL_RE.sub("\n\n", s)
    s = dedent_outside_fences(s)
    s = re.sub(r"(?m)^-\s*$", "", s)
    s = MULTI_NL_RE.sub("\n\n", s)
    return s.strip() + "\n"


def discover_links(html_text: str, page_url: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for href in HREF_RE.findall(html_text):
        norm = normalize_doc_url(href, page_url)
        if norm and norm not in seen:
            seen.add(norm)
            found.append(norm)
    return found


def token_line(rel: str, title: str, body: str) -> str:
    parts = [rel.replace("/", " ").replace(".md", "").replace("-", " "), title.lower()]
    parts.extend(h.lower() for h in re.findall(r"(?m)^#{2,4}\s+(.+)$", body)[:24])
    text = re.sub(r"[^a-z0-9_./+\- ]+", " ", " ".join(parts).lower())
    tokens: list[str] = []
    seen: set[str] = set()
    for tok in text.split():
        if tok in seen or len(tok) < 2:
            continue
        seen.add(tok)
        tokens.append(tok)
        if len(tokens) >= 48:
            break
    return " ".join(tokens)


def write_page(output_dir: str, url: str, html_text: str, final_url: str, generated_at: str) -> tuple[str, str, str]:
    rel = url_to_rel_md(url)
    path = os.path.join(output_dir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    title = extract_title(html_text, final_url)
    content = extract_balanced_div(html_text, div_id="content")
    if not content:
        content = extract_balanced_div(html_text, class_name="docpage-content__doc") or html_text
    body = html_to_llm_markdown(content, final_url)
    body_wo_dup = re.sub(rf"(?im)^#\s+{re.escape(title)}\s*\n+", "", body, count=1)
    body_final = body_wo_dup if body_wo_dup.strip() else body

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!-- src:{url} generated:{generated_at} format:llm-dense {DOC_TAG} -->\n")
        f.write(f"#DOC {rel}\n\n")
        f.write(f"# {title}\n\n")
        f.write(body_final)

    return rel, title, token_line(rel, title, body_final)


def write_index(output_dir: str, generated_at: str, rows: list[tuple[str, str, str]]) -> None:
    with open(os.path.join(output_dir, "index.md"), "w", encoding="utf-8") as f:
        f.write(f"# React4XP Offline Docs Index ({DOC_TAG})\n\n")
        f.write(f"Generated: {generated_at}\n")
        f.write("Format: llm-dense (cascade)\n")
        f.write("Shared base: `learn/react4xp/*`\n\n")
        f.write("Start URLs:\n")
        for seed in START_URLS:
            f.write(f"- {seed}\n")
        f.write("\n| File | Title | URL |\n")
        f.write("| --- | --- | --- |\n")
        for rel, title, url in rows:
            f.write(f"| `{rel}` | {title.replace('|', '\\|')} | {url} |\n")


def write_llm_index(output_dir: str, entries: list[tuple[str, str]]) -> None:
    with open(os.path.join(output_dir, "llm-index.md"), "w", encoding="utf-8") as f:
        f.write("# LLM_INDEX|machine|v1|path<TAB>tokens\n\n")
        for rel, tokens in sorted(entries):
            f.write(f"{rel}\t{tokens}\n")


def main() -> int:
    global PATH_PREFIXES, START_URLS, DOC_TAG

    _script_dir = Path(__file__).resolve().parent
    default_output = str((_script_dir / "../../../kb/offline-reference/react4xp-5.x").resolve())
    parser = argparse.ArgumentParser(description="Cascade-sync React4XP docs to LLM-dense markdown.")
    parser.add_argument(
        "--output",
        default=default_output,
        help="Output folder (default: ~/.agents/kb/offline-reference/react4xp-5.x)",
    )
    parser.add_argument(
        "--seed",
        action="append",
        help="Seed URL (repeatable). Default: https://developer.enonic.com/learn/react4xp-tutorial/5.x",
    )
    parser.add_argument(
        "--prefix",
        action="append",
        help="Allowed path prefix (repeatable). Default: /learn/react4xp-tutorial/5.x",
    )
    parser.add_argument("--tag", default="react4xp-5.x", help="Marker stored in file headers (e.g. react4xp-5.x)")
    parser.add_argument("--delay", type=float, default=0.05, help="Delay between requests in seconds")
    parser.add_argument("--max-pages", type=int, default=0, help="Optional cap (0 = unlimited)")
    args = parser.parse_args()

    START_URLS = list(args.seed) if args.seed else ["https://developer.enonic.com/learn/react4xp-tutorial/5.x"]
    PATH_PREFIXES = tuple(args.prefix) if args.prefix else ("/learn/react4xp-tutorial/5.x",)
    DOC_TAG = args.tag

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)
    generated_at = utc_now()

    queue: deque[str] = deque()
    queued: set[str] = set()
    for seed in START_URLS:
        norm = normalize_doc_url(seed)
        if norm and norm not in queued:
            queued.add(norm)
            queue.append(norm)

    rows: list[tuple[str, str, str]] = []
    llm_entries: list[tuple[str, str]] = []
    failures: list[tuple[str, str]] = []
    done: set[str] = set()

    while queue:
        if args.max_pages and len(done) >= args.max_pages:
            break

        url = queue.popleft()
        if url in done:
            continue

        try:
            html_text, final = fetch_html(url)
            final_norm = normalize_doc_url(final) or url
            for link in discover_links(html_text, final_norm):
                if link not in queued:
                    queued.add(link)
                    queue.append(link)
            rel, title, tokens = write_page(output_dir, final_norm, html_text, final_norm, generated_at)
            rows.append((rel, title, final_norm))
            llm_entries.append((rel, tokens))
            done.add(url)
            done.add(final_norm)
            print(f"[OK] {rel}")
        except urllib.error.HTTPError as e:
            failures.append((url, f"HTTP {e.code}"))
            done.add(url)
            print(f"[ERR] {url} -> HTTP {e.code}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            failures.append((url, str(e)))
            done.add(url)
            print(f"[ERR] {url} -> {e}", file=sys.stderr)

        if args.delay > 0:
            time.sleep(args.delay)

    rows.sort(key=lambda r: r[0])
    write_index(output_dir, generated_at, rows)
    write_llm_index(output_dir, llm_entries)

    print(f"\nSynced {len(rows)} pages -> {output_dir}")
    if failures:
        print(f"Failures: {len(failures)}", file=sys.stderr)
        for url, err in failures:
            print(f"- {url}: {err}", file=sys.stderr)
        return 0 if rows else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
