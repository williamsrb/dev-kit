#!/usr/bin/env python3
"""Sync a whitelisted slice of the Godot docs to LLM-dense offline markdown.

Source (pick one):
  --zip <path|url>   official offline HTML build (godot-docs-html-stable.zip)
  --crawl            polite crawl of https://docs.godotengine.org/en/<version>/

Examples:
  sync-godot-docs.py --crawl
  sync-godot-docs.py --zip ~/Downloads/godot-docs-html-stable.zip
  sync-godot-docs.py --crawl --dry-run

Output: ~/.agents/kb/offline-reference/godot/<docs path>.md (README.md and
llm-index.md v2 included). Pages carry no per-page date, so a re-run on the
same input rewrites identical bytes; only README.md holds the generated date.
Downloaded HTML is untrusted data: it is parsed, never executed.

Dependency: beautifulsoup4 (`bs4`), not stdlib; everything else is stdlib.
A source flag is required (no implicit default). Refuses to write into a
non-empty --output that is not this catalog (README.md with the catalog marker).
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError:
    sys.exit(
        "ERROR: sync-godot-docs.py needs beautifulsoup4 (pip install beautifulsoup4)"
    )

VERSION = "4.7"
HOST = "https://docs.godotengine.org/en/"
SKILL = "develop-godot"
UA = "agents-kb-godot-docs-sync/1.0 (offline reference build; polite crawl)"

KB = Path(__file__).resolve().parents[3] / "kb"
DEFAULT_OUTPUT = KB / "offline-reference" / "godot"
SHARED_SCRIPTS = KB / "_shared" / "scripts"

# Whole folders. Every prefix must match at least one page.
INCLUDE_PREFIXES = (
    "getting_started/step_by_step/",
    "getting_started/first_2d_game/",
    "getting_started/first_3d_game/",
    "tutorials/2d/",
    "tutorials/3d/",
    "tutorials/physics/",
    "tutorials/scripting/",
    "tutorials/inputs/",
    "tutorials/animation/",
    "tutorials/audio/",
    "tutorials/navigation/",
    "tutorials/ui/",
    "tutorials/io/",
    "tutorials/best_practices/",
    "tutorials/rendering/",
    "tutorials/shaders/shader_reference/",
    "tutorials/shaders/your_first_shader/",
)

# Single pages. Every entry must exist.
INCLUDE_DOCS = (
    "tutorials/3d/global_illumination/introduction_to_global_illumination",
    "tutorials/shaders/introduction_to_shaders",
    "tutorials/shaders/shaders_style_guide",
    "tutorials/export/exporting_projects",
    "tutorials/export/exporting_for_linux",
    "tutorials/export/exporting_for_windows",
    "tutorials/export/exporting_for_web",
    "tutorials/export/exporting_for_android",
    "tutorials/export/exporting_pcks",
    "tutorials/export/feature_tags",
    "tutorials/performance/general_optimization",
    "tutorials/performance/cpu_optimization",
    "tutorials/performance/gpu_optimization",
    "tutorials/performance/optimizing_3d_performance",
    "tutorials/performance/using_multimesh",
    "tutorials/editor/command_line_tutorial",
    *(f"tutorials/migrating/upgrading_to_godot_4.{n}" for n in range(3, 8)),
)

# Subtrees inside an included prefix that stay out (C#/C++ are not GDScript).
EXCLUDE_PREFIXES = (
    "tutorials/3d/global_illumination/",
    "tutorials/scripting/c_sharp/",
    "tutorials/scripting/cpp/",
    "tutorials/scripting/other_languages",
    "tutorials/rendering/compositor",
)
# Re-allowed despite EXCLUDE_PREFIXES.
EXCLUDE_EXCEPT = {
    "tutorials/3d/global_illumination/introduction_to_global_illumination"
}

# Class names (case-insensitive); entries with * are globs.
CLASSES = [
    "Node",
    "Node2D",
    "Node3D",
    "CanvasItem",
    "Control",
    "SceneTree",
    "Viewport",
    "Resource",
    "PackedScene",
    "ResourceLoader",
    "Input",
    "InputEvent*",
    "InputMap",
    "Timer",
    "Tween",
    "AnimationPlayer",
    "AnimationTree",
    "AnimationMixer",
    "AudioStreamPlayer",
    "AudioStreamPlayer2D",
    "AudioStreamPlayer3D",
    "Camera2D",
    "Camera3D",
    "Sprite2D",
    "Sprite3D",
    "AnimatedSprite2D",
    "AnimatedSprite3D",
    "TileMapLayer",
    "TileSet",
    "TileMap",
    "CharacterBody2D",
    "CharacterBody3D",
    "RigidBody2D",
    "RigidBody3D",
    "StaticBody2D",
    "StaticBody3D",
    "AnimatableBody2D",
    "AnimatableBody3D",
    "Area2D",
    "Area3D",
    "CollisionShape2D",
    "CollisionShape3D",
    "CollisionPolygon2D",
    "RayCast2D",
    "RayCast3D",
    "ShapeCast2D",
    "ShapeCast3D",
    "PhysicsBody2D",
    "PhysicsBody3D",
    "PhysicsDirectSpaceState2D",
    "PhysicsDirectSpaceState3D",
    "NavigationAgent2D",
    "NavigationAgent3D",
    "NavigationRegion2D",
    "NavigationRegion3D",
    "Parallax2D",
    "CanvasLayer",
    "MeshInstance3D",
    "StandardMaterial3D",
    "BaseMaterial3D",
    "WorldEnvironment",
    "Environment",
    "DirectionalLight3D",
    "OmniLight3D",
    "SpotLight3D",
    "GPUParticles2D",
    "GPUParticles3D",
    "CPUParticles2D",
    "ProjectSettings",
    "FileAccess",
    "DirAccess",
    "ConfigFile",
    "JSON",
    "Engine",
    "OS",
    "@GDScript",
    "@GlobalScope",
    "Callable",
    "Signal",
    "Array",
    "Dictionary",
    "String",
    "Vector2",
    "Vector3",
    "Transform2D",
    "Transform3D",
    "Basis",
    "SpringArm3D",
    "GridMap",
    "Label",
    "Button",
    "Container",
    "BoxContainer",
    "HBoxContainer",
    "VBoxContainer",
    "MarginContainer",
    "GridContainer",
    "Theme",
    "AreaLight3D",
    "Light3D",
    "MultiMesh",
    "MultiMeshInstance2D",
    "MultiMeshInstance3D",
]

SKIP_TAGS = {
    "script",
    "style",
    "noscript",
    "nav",
    "footer",
    "button",
    "hr",
    "svg",
    "form",
    "iframe",
}
HEADINGS = {f"h{i}": "#" * i for i in range(1, 7)}
INLINE_TAGS = {
    "a",
    "abbr",
    "b",
    "cite",
    "code",
    "em",
    "i",
    "kbd",
    "samp",
    "span",
    "strong",
    "sub",
    "sup",
    "tt",
    "var",
    "br",
    "img",
    "small",
    "u",
    "s",
    "del",
    "ins",
    "mark",
    "q",
    "wbr",
    "label",
}
FENCE_LANG_SKIP = {"default", "none", "text", "default-literal"}
NOISE_LINES = re.compile(
    r"^(Previous|Next|Built with Sphinx.*|User-contributed notes|© Copyright.*|"
    r"Please read the User-contributed notes policy.*)$"
)
IMG_ALT_BAD = re.compile(r"(/|\.(png|jpe?g|gif|webp|svg)$)", re.IGNORECASE)


# --------------------------------------------------------------------------- selection


def class_docnames(all_docs: set[str]) -> tuple[set[str], list[str]]:
    chosen: set[str] = set()
    missing: list[str] = []
    for name in CLASSES:
        pattern = f"classes/class_{name.lower()}"
        hits = fnmatch.filter(sorted(all_docs), pattern)
        if not hits:
            missing.append(pattern)
        chosen.update(hits)
    return chosen, missing


def select_docs(all_docs: set[str]) -> tuple[list[str], list[str]]:
    """Return (sorted whitelisted docnames, missing whitelist entries)."""
    all_docs = {
        d for d in all_docs if not d.startswith("/") and ".." not in d.split("/")
    }
    chosen: set[str] = set()
    missing: list[str] = []
    for prefix in INCLUDE_PREFIXES:
        hits = {
            d
            for d in all_docs
            if d.startswith(prefix) and PurePosixPath(d).name != "index"
        }
        hits = {
            d
            for d in hits
            if not any(d.startswith(x) for x in EXCLUDE_PREFIXES) or d in EXCLUDE_EXCEPT
        }
        if not hits:
            missing.append(prefix + "*")
        chosen |= hits
    for doc in INCLUDE_DOCS:
        if doc in all_docs:
            chosen.add(doc)
        else:
            missing.append(doc)
    classes, class_missing = class_docnames(all_docs)
    chosen |= classes
    missing += class_missing
    return sorted(chosen), missing


# --------------------------------------------------------------------------- sources


class CrawlSource:
    def __init__(
        self, version: str, delay: float, retries: int, cache_dir: Path | None
    ):
        self.base = f"{HOST}{version}/"
        self.delay = delay
        self.retries = retries
        self.cache_dir = cache_dir
        self.label = f"crawl {self.base}"
        self._last = 0.0

    def _get(self, url: str) -> str:
        last_err: Exception | None = None
        for attempt in range(self.retries):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "text/html,*/*"}
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except urllib.error.HTTPError as exc:
                last_err = exc
                if exc.code == 404:
                    break
            except (urllib.error.URLError, TimeoutError) as exc:
                last_err = exc
            time.sleep(2**attempt)
        raise RuntimeError(f"{url}: {last_err}")

    def _cached(self, name: str, url: str) -> str:
        if self.cache_dir:
            path = self.cache_dir / name
            if path.is_file():
                return path.read_text(encoding="utf-8")
        text = self._get(url)
        if self.cache_dir:
            path = self.cache_dir / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return text

    def docnames(self) -> set[str]:
        raw = self._cached("searchindex.js", self.base + "searchindex.js")
        data = json.loads(raw[raw.index("(") + 1 : raw.rindex(")")])
        return set(data["docnames"])

    def page(self, doc: str) -> str:
        return self._cached(f"{doc}.html", f"{self.base}{doc}.html")

    def index_html(self) -> str:
        return self._cached("index.html", self.base)


class ZipSource:
    def __init__(self, path: Path):
        self.zf = zipfile.ZipFile(path)
        names = self.zf.namelist()
        roots = [
            n[: -len("searchindex.js")] for n in names if n.endswith("searchindex.js")
        ]
        if not roots:
            roots = [n[: -len("index.html")] for n in names if n.endswith("index.html")]
        if not roots:
            raise RuntimeError(f"{path}: no searchindex.js or index.html in archive")
        self.root = min(roots, key=len)
        self.label = f"zip {path.name}"

    def docnames(self) -> set[str]:
        n = len(self.root)
        return {
            x[n:-5]
            for x in self.zf.namelist()
            if x.startswith(self.root) and x.endswith(".html")
        }

    def page(self, doc: str) -> str:
        return self.zf.read(f"{self.root}{doc}.html").decode("utf-8", errors="replace")

    def index_html(self) -> str:
        return self.page("index")


def fetch_zip(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "godot-docs.zip"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as resp, dest.open("wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
    return dest


def verify_branch(html: str, version: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta = soup.find("meta", attrs={"name": "doc_version"})
    meta_ver = meta.get("content", "") if isinstance(meta, Tag) else ""
    if meta_ver == version or f"{version} branch" in title:
        return f"title='{title}' doc_version='{meta_ver}'"
    raise RuntimeError(
        f"not the {version} branch: title='{title}' doc_version='{meta_ver}'"
    )


# --------------------------------------------------------------------------- conversion


class Converter:
    def __init__(self, docs: set[str], version: str):
        self.docs = docs
        self.base = f"{HOST}{version}/"

    # inline ---------------------------------------------------------------

    def href(self, href: str, doc: str) -> str | None:
        """Offline link target, or None when the link should drop to plain text."""
        href = href.strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            return None
        if re.match(r"https?://", href):
            m = re.match(
                r"https://docs\.godotengine\.org/en/(?:stable|latest|\d+\.\d+)/(.*?)(?:\.html)?(?:#.*)?$",
                href,
            )
            if not m:
                return href
            target = m.group(1)
        else:
            target = href.split("#")[0]
            if not target.endswith(".html"):
                return None
            target = os.path.normpath(
                os.path.join(os.path.dirname(doc), target[: -len(".html")])
            )
        target = target.strip("/")
        if target not in self.docs:
            return None
        rel = os.path.relpath(target, os.path.dirname(doc) or ".")
        return rel + ".md"

    def inline(self, node: Tag | NavigableString, doc: str) -> str:
        if isinstance(node, NavigableString):
            return str(node) if type(node) is NavigableString else ""
        name = node.name
        classes = node.get("class") or []
        if name in SKIP_TAGS or "headerlink" in classes:
            return ""
        if name == "br":
            return " "
        if name == "img":
            alt = (node.get("alt") or "").strip()
            return (
                f" [image: {alt}] "
                if alt and len(alt) > 3 and not IMG_ALT_BAD.search(alt)
                else ""
            )
        if name in ("code", "kbd", "samp", "tt"):
            text = re.sub(r"\s+", " ", node.get_text()).strip()
            if not text:
                return ""
            return f"``{text}``" if "`" in text else f"`{text}`"
        inner = "".join(self.inline(c, doc) for c in node.children)
        if name in ("strong", "b"):
            return f"**{inner.strip()}**" if inner.strip() else ""
        if name in ("em", "i", "cite"):
            return f"*{inner.strip()}*" if inner.strip() else ""
        if name == "a":
            target = self.href(node.get("href") or "", doc)
            label = inner.strip()
            if target and label:
                return f"[{label}]({target})"
            return inner
        return inner

    def text(self, node: Tag, doc: str) -> str:
        raw = "".join(self.inline(c, doc) for c in node.children)
        return re.sub(r"\s+", " ", raw).strip()

    # blocks ---------------------------------------------------------------

    def children_blocks(self, node: Tag, doc: str) -> list[str]:
        out: list[str] = []
        buf: list[str] = []

        def flush() -> None:
            joined = re.sub(r"\s+", " ", "".join(buf)).strip()
            buf.clear()
            if joined:
                out.append(joined)

        for child in node.children:
            if isinstance(child, NavigableString):
                if type(child) is NavigableString:
                    buf.append(str(child))
                continue
            is_inline = child.name in INLINE_TAGS and not (
                child.name == "span"
                and child.find(["div", "p", "pre", "ul", "ol", "table"])
            )
            if is_inline:
                buf.append(self.inline(child, doc))
                continue
            flush()
            out.extend(self.block(child, doc))
        flush()
        return out

    def block(self, el: Tag, doc: str) -> list[str]:
        name = el.name
        classes = el.get("class") or []
        if (
            name in SKIP_TAGS
            or "headerlink" in classes
            or "rst-footer-buttons" in classes
        ):
            return []
        if name in HEADINGS:
            if name == "h1":
                return []
            t = self.text(el, doc)
            return [f"{HEADINGS[name]} {t}"] if t else []
        if name == "p":
            t = self.text(el, doc)
            return [t] if t else []
        if name in ("ul", "ol"):
            return self.list_block(el, doc)
        if name == "pre":
            return [self.fence(el, "")]
        if name == "table":
            return self.table(el, doc)
        if name == "dl":
            return self.dl(el, doc)
        if name == "blockquote":
            return self.quote(self.children_blocks(el, doc), None)
        if name == "figure":
            return self.children_blocks(el, doc)
        if name == "div":
            hl = next(
                (c[len("highlight-") :] for c in classes if c.startswith("highlight-")),
                None,
            )
            if hl is not None:
                pre = el.find("pre")
                return [self.fence(pre, hl)] if pre else []
            if "highlight" in classes:
                pre = el.find("pre")
                return [self.fence(pre, "")] if pre else []
            if "sphinx-tabs" in classes:
                return self.tabs(el, doc)
            if "admonition" in classes:
                return self.admonition(el, classes, doc)
        return self.children_blocks(el, doc)

    @staticmethod
    def fence(pre: Tag, lang: str) -> str:
        if lang in FENCE_LANG_SKIP:
            lang = ""
        for junk in pre.select("button, .copybtn"):
            junk.decompose()
        code = pre.get_text().replace("\r", "").rstrip("\n")
        return f"```{lang}\n{code}\n```"

    def list_block(self, el: Tag, doc: str) -> list[str]:
        lines: list[str] = []
        ordered = el.name == "ol"
        for i, li in enumerate(el.find_all("li", recursive=False), 1):
            marker = f"{i}." if ordered else "-"
            blocks = self.children_blocks(li, doc)
            if not blocks:
                continue
            pad = " " * (len(marker) + 1)
            first, rest = blocks[0], blocks[1:]
            body = [f"{marker} {first.splitlines()[0]}"] + [
                pad + ln for ln in first.splitlines()[1:]
            ]
            for b in rest:
                body += [pad + ln if ln else ln for ln in b.splitlines()]
            lines.append("\n".join(body))
        return ["\n".join(lines)] if lines else []

    def table(self, el: Tag, doc: str) -> list[str]:
        has_head = el.find("thead") is not None
        rows: list[list[str]] = []
        for tr in el.find_all("tr"):
            cells = []
            for td in tr.find_all(["th", "td"], recursive=False):
                blocks = self.children_blocks(td, doc)
                cell = " ".join(b.replace("\n", " ") for b in blocks)
                cells.append(cell.replace("|", "\\|").strip())
            if cells:
                rows.append(cells)
        if not rows:
            return []
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]
        if has_head:
            head, body = rows[0], rows[1:]
            lines = [
                "| " + " | ".join(head) + " |",
                "| " + " | ".join("---" for _ in head) + " |",
            ]
            lines += ["| " + " | ".join(r) + " |" for r in body]
        else:
            lines = [" | ".join(r).rstrip() for r in rows]
        return ["\n".join(lines)]

    def dl(self, el: Tag, doc: str) -> list[str]:
        out: list[str] = []
        term = ""
        for child in el.find_all(["dt", "dd"], recursive=False):
            if child.name == "dt":
                term = self.text(child, doc)
                continue
            body = self.children_blocks(child, doc)
            if not body:
                out.append(term)
                continue
            head = f"**{term}**: {body[0]}" if term else body[0]
            out.append(head)
            out.extend(body[1:])
        return [b for b in out if b]

    @staticmethod
    def quote(blocks: list[str], label: str | None) -> list[str]:
        if not blocks:
            return []
        if label:
            blocks = [f"**{label}:** {blocks[0]}"] + blocks[1:]
        if any(b.startswith("```") for b in blocks):
            return blocks
        lines = "\n>\n".join(
            "\n".join("> " + ln for ln in b.splitlines()) for b in blocks
        )
        return [lines]

    def admonition(self, el: Tag, classes: list[str], doc: str) -> list[str]:
        title_el = el.find("p", class_="admonition-title", recursive=False)
        label = self.text(title_el, doc) if title_el else ""
        if not label:
            kind = next((c for c in classes if c != "admonition"), "note")
            label = kind.capitalize()
        if title_el:
            title_el.extract()
        return self.quote(self.children_blocks(el, doc), label)

    def tabs(self, el: Tag, doc: str) -> list[str]:
        root = el.find_parent("body") or el
        panels = el.find_all("div", class_="sphinx-tabs-panel", recursive=False)
        has_gd = any(p.select_one('div[class*="highlight-gdscript"]') for p in panels)
        out: list[str] = []
        for panel in panels:
            if has_gd and panel.select_one('div[class*="highlight-csharp"]'):
                continue
            btn = (
                root.find(id=panel.get("aria-labelledby"))
                if panel.get("aria-labelledby")
                else None
            )
            label = btn.get_text(" ", strip=True) if btn else ""
            label = re.sub(r"\bGDScript\b", "", label).strip()
            if label:
                out.append(f"**{label}**")
            out.extend(self.children_blocks(panel, doc))
        return out

    # page -----------------------------------------------------------------

    def convert(self, html: str, doc: str) -> tuple[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        main = (
            soup.select_one('div[role="main"]') or soup.select_one("main") or soup.body
        )
        if main is None:
            raise RuntimeError(f"{doc}: no main content")
        h1 = main.find("h1")
        title = self.text(h1, doc) if h1 else doc
        blocks = self.children_blocks(main, doc)
        for i, b in enumerate(blocks):
            if re.match(r"#{2,6} User-contributed notes", b):
                blocks = blocks[:i]
                break
        blocks = [b for b in blocks if not NOISE_LINES.match(b.strip())]
        body = "\n\n".join(blocks)
        body = re.sub(r"[ \t]+\n", "\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        return title, body


def render_page(version: str, doc: str, title: str, body: str) -> str:
    rel = doc + ".md"
    return (
        f"<!-- src:{HOST}{version}/{doc}.html format:llm-dense godot-{version} -->\n"
        f"#DOC {rel}\n\n# {title}\n\n{body}\n"
    )


# --------------------------------------------------------------------------- output


def write_text_if_changed(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8")


def build_indexes(output: Path) -> None:
    """Rebuild v2 llm-index.md files and fill the skills column."""
    sys.path.insert(0, str(SHARED_SCRIPTS))
    import llm_index

    mapping = {SKILL: SKILL}
    llm_index.write_bucket_indexes(output, mapping)
    for sub in ("getting_started", "tutorials", "tutorials/scripting"):
        folder = output / sub
        if folder.is_dir():
            llm_index.write_bucket_indexes(folder, mapping)
    for idx in output.rglob("llm-index.md"):
        lines = idx.read_text(encoding="utf-8").splitlines()
        fixed = []
        for ln in lines:
            parts = ln.split("\t")
            if len(parts) == 5 and not parts[0].startswith("#"):
                parts[3] = SKILL
                ln = "\t".join(parts)
            fixed.append(ln)
        idx.write_text("\n".join(fixed) + "\n", encoding="utf-8")


def write_readme(
    output: Path,
    version: str,
    source: str,
    evidence: str,
    stats: dict[str, int],
    tokens: int,
) -> None:
    today = dt.datetime.now(dt.UTC).date().isoformat()
    rows = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(stats.items()))
    text = f"""# Godot {version} offline docs

Version: {version} (docs branch `{version}`; no unpinned `stable` alias in page headers)
Source: {source}
Branch evidence: {evidence}
Generated: {today}
Pages: {sum(stats.values())}, about {tokens} tokens (chars/4)
Used by: `{SKILL}`

Layout: docs path with `.html` replaced by `.md`, for example `classes/class_tilemaplayer.md`, `tutorials/2d/using_tilemaps.md`. Route via `llm-index.md` (`path<TAB>tokens<TAB>topic<TAB>skills<TAB>keywords`). Class pages are catalogs: read by section, never whole.

Conversion notes:
- Main content only. Sphinx/RTD chrome, Previous/Next, user notes, version banners and images are dropped (image alt text kept when meaningful).
- Code fences carry the Sphinx language (`gdscript`, `ini`, `shell`, ...). Where a page shows GDScript and C# tabs, only GDScript is kept. A C#-only block with no GDScript twin stays.
- Links to pages outside this catalog, and same-page anchors, become plain text. Links to catalog pages are relative `.md` paths without fragments.
- Section `index` pages (pure toctrees) are excluded.
- Pages have no per-page date, so re-runs diff cleanly.

## Pages by folder

| Folder | Pages |
| --- | --- |
{rows}

## Refresh

Needs `beautifulsoup4` (`bs4`) besides the stdlib. A source flag is required.

```bash
python3 ~/.agents/skills/{SKILL}/scripts/sync-godot-docs.py --version 4.7 --crawl --cache-dir ~/.local/share/godot/docs-src/<date>/html
# or, from the official offline build:
python3 ~/.agents/skills/{SKILL}/scripts/sync-godot-docs.py --version 4.7 --zip <godot-docs-html-stable.zip|url>
# then rebuild the search index over ALL catalogs (each run drops the table):
~/.agents/bin/agentctl docs index $(for d in ~/.agents/kb/offline-reference/*/; do n=$(basename $d); [ $n = scripts ] || echo --root ${{d%/}}; done) --db ~/.agents/.cache/offline-docs.sqlite
```

Do NOT run `compact_offline_reference.py` on this catalog: footers are stripped at conversion and it blanks the skills column of `llm-index.md`. If it was run, repair with `sync-godot-docs.py --reindex`.
"""
    write_text_if_changed(output / "README.md", text)


def folder_key(doc: str) -> str:
    parts = doc.split("/")
    if parts[0] == "classes":
        return "classes"
    return "/".join(parts[:2]) if len(parts) > 2 else parts[0]


CATALOG_MARKER = "Used by: `develop-godot`"


def check_output_dir(output: Path) -> None:
    """Refuse to write into (and later prune) a directory that is not this catalog."""
    if not output.exists() or not any(output.iterdir()):
        return
    readme = output / "README.md"
    head = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    if not (head.startswith("# Godot ") and CATALOG_MARKER in head):
        sys.exit(
            f"ERROR: {output} is non-empty and is not a Godot catalog (README.md marker missing)"
        )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sync whitelisted Godot docs to LLM-dense markdown."
    )
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--zip", help="Offline HTML zip: local path or URL")
    src.add_argument(
        "--crawl", action="store_true", help=f"Crawl {HOST}<version>/ politely"
    )
    src.add_argument(
        "--reindex",
        action="store_true",
        help="Only rebuild llm-index.md files in --output",
    )
    ap.add_argument(
        "--version", default=VERSION, help="Docs branch to pin (default: %(default)s)"
    )
    ap.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Catalog root (default: %(default)s)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="List the selection and counts; write nothing",
    )
    ap.add_argument(
        "--delay", type=float, default=0.3, help="Crawl delay between requests (s)"
    )
    ap.add_argument("--retries", type=int, default=3, help="Crawl retries per request")
    ap.add_argument(
        "--cache-dir", help="Crawl only: keep raw HTML here and reuse it on re-runs"
    )
    ap.add_argument(
        "--download-dir", help="Where a --zip URL is saved (must be new or empty)"
    )
    args = ap.parse_args()

    output = Path(args.output).expanduser().resolve()
    if args.reindex:
        build_indexes(output)
        print(f"reindexed {output}")
        return 0
    if not (args.zip or args.crawl):
        ap.error(
            "pick a source: --crawl [--cache-dir DIR], --zip <path|url>, or --reindex"
        )

    check_output_dir(output)
    if args.zip:
        zip_arg = args.zip
        if re.match(r"https?://", zip_arg):
            dest = Path(
                args.download_dir or tempfile.mkdtemp(prefix="godot-docs-")
            ).expanduser()
            if dest.exists() and any(dest.iterdir()):
                ap.error(f"--download-dir {dest} is not empty")
            zip_path = fetch_zip(zip_arg, dest)
        else:
            zip_path = Path(zip_arg).expanduser()
        source = ZipSource(zip_path)
        source_desc = f"official offline HTML build `{zip_arg}`"
    else:
        cache = Path(args.cache_dir).expanduser() if args.cache_dir else None
        source = CrawlSource(args.version, args.delay, args.retries, cache)
        source_desc = f"crawl of {HOST}{args.version}/"

    try:
        evidence = verify_branch(source.index_html(), args.version)
        all_docs = source.docnames()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    docs, missing = select_docs(all_docs)
    stats: dict[str, int] = {}
    for d in docs:
        stats[folder_key(d)] = stats.get(folder_key(d), 0) + 1
    print(
        f"selected {len(docs)} pages from {len(all_docs)} ({source.label}); {evidence}"
    )
    for key, n in sorted(stats.items()):
        print(f"  {key}: {n}")
    if missing:
        print(
            f"ERROR: {len(missing)} whitelist entries missing from source:",
            file=sys.stderr,
        )
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1
    if args.dry_run:
        return 0

    conv = Converter(set(docs), args.version)
    failures: list[str] = []
    total_chars = 0
    written: set[Path] = set()
    for doc in docs:
        try:
            title, body = conv.convert(source.page(doc), doc)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{doc}: {exc}")
            continue
        text = render_page(args.version, doc, title, body)
        total_chars += len(text)
        path = output / f"{doc}.md"
        write_text_if_changed(path, text)
        written.add(path)
    if failures:
        print(f"ERROR: {len(failures)} pages failed:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    for stale in output.rglob("*.md"):
        if stale not in written and stale.name not in ("README.md", "llm-index.md"):
            stale.unlink()
    write_readme(output, args.version, source_desc, evidence, stats, total_chars // 4)
    build_indexes(output)
    print(f"wrote {len(written)} pages, about {total_chars // 4} tokens -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
