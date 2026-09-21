#!/usr/bin/env python3
"""Export a Cursor `.canvas.tsx` file to a self-contained HTML page.

Transforms the canvas the same way the IDE does (esbuild JSX, strip
`cursor/canvas` imports) and mounts it with Cursor's official
`canvas-runtime.esm.js` plus the live canvas host stylesheet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = SKILL_DIR / "runtime"


def agents_home() -> Path:
    raw = os.environ.get("AGENTS_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".agents"


CACHE_DIR = agents_home() / ".cache" / "export-canvas-html"
PROJECTS_DIR = Path.home() / ".cursor" / "projects"
IMPORT_LINE_RE = re.compile(r"^\s*import\b[\s\S]*?;\s*$", re.MULTILINE)
CANVAS_IMPORT_RE = re.compile(r"""from\s+['"]cursor/canvas['"]""")
RELATIVE_IMPORT_RE = re.compile(r"""from\s+['"]\.\.?/""")
DEFAULT_EXPORT_RE = re.compile(r"\bexport\s+default\b")
RUNTIME_CANDIDATES = (
    Path("/usr/share/cursor/resources/app/extensions/cursor-agent-exec/dist/canvas-runtime/canvas-runtime.esm.js"),
    Path("/usr/share/cursor/resources/app/extensions/cursor-agent-host/dist/canvas-runtime/canvas-runtime.esm.js"),
    RUNTIME_DIR / "canvas-runtime.esm.js",
)


class ExportError(Exception):
    """User-facing failure. Message is printed as JSON."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a Cursor .canvas.tsx file into a self-contained HTML page "
            "using Cursor's canvas-runtime.esm.js."
        )
    )
    parser.add_argument(
        "canvas",
        nargs="?",
        help=(
            "Path to a .canvas.tsx file, or a slug matched under "
            "~/.cursor/projects/*/canvases/. Omit with --list."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help=(
            "Destination .html file, or a directory (writes index.html). "
            "Defaults to a new temporary directory."
        ),
    )
    parser.add_argument(
        "--theme",
        choices=("auto", "light", "dark"),
        default="auto",
        help=(
            "Host theme kind seeded into __cursorCanvas.state "
            "(same channel the IDE runtime reads). Default: auto."
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print known canvases as JSON and exit.",
    )
    parser.add_argument(
        "--keep-dist",
        action="store_true",
        help="Also write canvas-runtime.esm.js and app.js next to the HTML.",
    )
    parser.add_argument(
        "--force-install",
        action="store_true",
        help="Re-run npm install in the dependency cache.",
    )
    parser.add_argument(
        "--title",
        help="HTML document title. Defaults to the canvas stem.",
    )
    return parser.parse_args(argv)


def emit(payload: dict, code: int) -> int:
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return code


def which(name: str) -> Path:
    path = shutil.which(name)
    if not path:
        raise ExportError(f"Required executable not found on PATH: {name}")
    return Path(path)


def node_major(node_bin: Path) -> tuple[str, int]:
    result = subprocess.run(
        [str(node_bin), "-v"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ExportError(f"node -v failed: {result.stderr.strip() or result.stdout.strip()}")
    version = result.stdout.strip().lstrip("v")
    try:
        major = int(version.split(".", 1)[0])
    except ValueError as exc:
        raise ExportError(f"Unparseable node version: {version!r}") from exc
    return version, major


def package_stamp() -> str:
    package_json = (RUNTIME_DIR / "package.json").read_bytes()
    lock = RUNTIME_DIR / "package-lock.json"
    payload = package_json
    if lock.is_file():
        payload += b"\n" + lock.read_bytes()
    return hashlib.sha256(payload).hexdigest()


def ensure_install(force: bool) -> Path:
    if not (RUNTIME_DIR / "package.json").is_file():
        raise ExportError(f"Missing runtime package.json at {RUNTIME_DIR / 'package.json'}")

    npm_bin = which("npm")
    which("node")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = package_stamp()
    stamp_path = CACHE_DIR / ".stamp"
    esbuild_bin = CACHE_DIR / "node_modules" / ".bin" / "esbuild"
    cached = (
        stamp_path.is_file()
        and stamp_path.read_text(encoding="utf-8").strip() == stamp
        and esbuild_bin.is_file()
    )
    if cached and not force:
        return CACHE_DIR

    shutil.copy2(RUNTIME_DIR / "package.json", CACHE_DIR / "package.json")
    lock = RUNTIME_DIR / "package-lock.json"
    cache_lock = CACHE_DIR / "package-lock.json"
    if lock.is_file():
        shutil.copy2(lock, cache_lock)
        cmd = [str(npm_bin), "ci", "--omit=dev", "--no-fund", "--no-audit"]
    else:
        if cache_lock.is_file():
            cache_lock.unlink()
        cmd = [str(npm_bin), "install", "--omit=dev", "--no-fund", "--no-audit"]

    print(f"Installing npm dependencies into {CACHE_DIR} …", file=sys.stderr)
    result = subprocess.run(cmd, cwd=CACHE_DIR, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ExportError(f"npm install failed:\n{detail}")
    if not esbuild_bin.is_file():
        raise ExportError(f"esbuild binary missing after install: {esbuild_bin}")
    stamp_path.write_text(stamp + "\n", encoding="utf-8")
    return CACHE_DIR


def discover_canvases() -> list[Path]:
    if not PROJECTS_DIR.is_dir():
        return []
    found: list[Path] = []
    for canvases_dir in sorted(PROJECTS_DIR.glob("*/canvases")):
        found.extend(sorted(canvases_dir.glob("*.canvas.tsx")))
    return found


def resolve_canvas(spec: str) -> Path:
    raw = Path(spec).expanduser()
    if raw.exists():
        return raw.resolve()

    matches: list[Path] = []
    slug = spec.removesuffix(".canvas.tsx").removesuffix(".tsx")
    for path in discover_canvases():
        stem = path.name.removesuffix(".canvas.tsx")
        if stem == slug or path.name == spec:
            matches.append(path)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        listed = "\n".join(f"  {p}" for p in matches)
        raise ExportError(f"Slug {spec!r} matches multiple canvases:\n{listed}")
    raise ExportError(
        f"Canvas not found: {spec}. Pass an absolute .canvas.tsx path, or use --list."
    )


def validate_canvas(path: Path) -> None:
    if not path.is_file():
        raise ExportError(f"Not a file: {path}")
    if path.suffix != ".tsx":
        raise ExportError(f"Expected a .tsx canvas file, got {path}")
    text = path.read_text(encoding="utf-8")
    if not CANVAS_IMPORT_RE.search(text):
        raise ExportError(
            f"{path} does not import from 'cursor/canvas'. "
            "This exporter only handles Cursor canvas files."
        )
    if RELATIVE_IMPORT_RE.search(text):
        raise ExportError(
            f"{path} has a relative import. Cursor canvases must import only from "
            "'cursor/canvas'; the exporter will not follow local modules."
        )
    if not DEFAULT_EXPORT_RE.search(text):
        raise ExportError(
            f"{path} has no `export default`. The web host mounts the default export."
        )


def canvas_stem(path: Path) -> str:
    name = path.name
    if name.endswith(".canvas.tsx"):
        return name[: -len(".canvas.tsx")]
    return path.stem


def resolve_output(output: Path | None, stem: str) -> tuple[Path, Path | None]:
    if output is None:
        out_dir = Path(tempfile.mkdtemp(prefix="export-canvas-html-"))
        return out_dir / f"{stem}.html", None
    dest = output.expanduser().resolve()
    if dest.suffix.lower() == ".html" or (not dest.exists() and dest.suffix):
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest, dest.parent / f"{dest.stem}-dist"
    dest.mkdir(parents=True, exist_ok=True)
    return dest / "index.html", dest / "dist"


def find_canvas_runtime() -> Path:
    for path in RUNTIME_CANDIDATES:
        if path.is_file():
            return path
    listed = "\n".join(f"  {p}" for p in RUNTIME_CANDIDATES)
    raise ExportError(
        "Cursor canvas-runtime.esm.js not found. Install Cursor or copy the "
        f"runtime next to the skill.\nTried:\n{listed}"
    )


def sidecar_data(canvas: Path) -> dict:
    path = canvas.with_suffix(".data.json")
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict) and not isinstance(payload, list):
        return payload
    return {}


def transform_canvas(canvas: Path) -> str:
    esbuild_bin = CACHE_DIR / "node_modules" / ".bin" / "esbuild"
    source = canvas.read_text(encoding="utf-8")
    result = subprocess.run(
        [
            str(esbuild_bin),
            "--loader=tsx",
            f"--sourcefile={canvas.name}",
            "--jsx=transform",
            "--jsx-factory=React.createElement",
            "--jsx-fragment=React.Fragment",
            "--format=esm",
            "--target=es2022",
        ],
        input=source,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ExportError(f"esbuild transform failed:\n{detail}")
    code = IMPORT_LINE_RE.sub("", result.stdout)
    if not code.strip():
        raise ExportError("Canvas build completed without producing output.")
    return code


def js_string(value: str) -> str:
    return json.dumps(value).replace("<", "\\u003c")


# Workbench colors the IDE pushes on the live canvas host (`__cursorCanvas.state`).
# Light matches Cursor / VS Code Light Modern as observed on the live localhost canvas.
THEME_PRESETS = {
    "light": {
        "kind": "light",
        "primary": "#005fb8",
        "editorBackground": "#ffffff",
        "editorForeground": "#3b3b3b",
    },
    "dark": {
        "kind": "dark",
        "primary": "#3794ff",
        "editorBackground": "#181818",
        "editorForeground": "#cccccc",
    },
}


def build_boot(runtime_js: str, app_js: str, theme: str, data: dict) -> str:
    state_entries: list = []
    preset = THEME_PRESETS.get(theme)
    if preset is not None:
        state_entries.append(["theme", preset])
    data_entries = [[key, value] for key, value in data.items()]
    return "\n".join(
        [
            f"const RUNTIME = {js_string(runtime_js)};",
            f"const APP = {js_string(app_js)};",
            "window.__cursorCanvas = {",
            "  canvasId: undefined,",
            "  tokenParam: '',",
            f"  state: new Map({json.dumps(state_entries)}),",
            f"  data: new Map({json.dumps(data_entries)}),",
            "  reportError() {}",
            "};",
            "const { mountCanvas } = await import(",
            "  URL.createObjectURL(new Blob([RUNTIME], { type: 'text/javascript' })),",
            ");",
            "await mountCanvas(",
            "  URL.createObjectURL(new Blob([APP], { type: 'text/javascript' })),",
            ");",
        ]
    )


def build_html(title: str, boot: str) -> str:
    host_css = (RUNTIME_DIR / "host.css").read_text(encoding="utf-8").strip()
    template = (RUNTIME_DIR / "index.html").read_text(encoding="utf-8")
    return (
        template.replace("__TITLE__", title)
        .replace("__HOST_CSS__", host_css)
        .replace("__BOOT__", boot)
    )


def file_url(path: Path) -> str:
    return path.resolve().as_uri()


def list_payload() -> dict:
    canvases = discover_canvases()
    return {
        "ok": True,
        "count": len(canvases),
        "canvases": [str(p) for p in canvases],
    }


def export_canvas(args: argparse.Namespace) -> dict:
    if not args.canvas:
        raise ExportError("Pass a canvas path or slug, or use --list.")
    canvas = resolve_canvas(args.canvas)
    validate_canvas(canvas)
    stem = canvas_stem(canvas)
    title = args.title or stem.replace("-", " ")
    node_bin = which("node")
    version, major = node_major(node_bin)
    if major < 18:
        raise ExportError(f"Node 18+ is required (found v{version}).")

    ensure_install(force=args.force_install)
    runtime_path = find_canvas_runtime()
    runtime_js = runtime_path.read_text(encoding="utf-8")
    app_js = transform_canvas(canvas)
    html_path, dist_keep = resolve_output(args.output, stem)
    boot = build_boot(runtime_js, app_js, args.theme, sidecar_data(canvas))
    html_path.write_text(build_html(title, boot), encoding="utf-8")

    keep = None
    if args.keep_dist:
        keep = dist_keep if dist_keep is not None else html_path.parent / "dist"
        if keep.exists():
            shutil.rmtree(keep)
        keep.mkdir(parents=True, exist_ok=True)
        shutil.copy2(runtime_path, keep / "canvas-runtime.esm.js")
        (keep / "app.js").write_text(app_js, encoding="utf-8")

    result = {
        "ok": True,
        "canvas": str(canvas),
        "html": str(html_path),
        "url": file_url(html_path),
        "theme": args.theme,
        "title": title,
        "shim": "cursor-canvas-runtime.esm",
        "runtime": str(runtime_path),
        "node": version,
        "notes": [
            "Host CSS and primitives come from Cursor's live canvas-runtime.",
            "useCanvasAction is a no-op outside the IDE.",
        ],
    }
    if keep is not None:
        result["dist"] = str(keep)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.list:
            return emit(list_payload(), 0)
        return emit(export_canvas(args), 0)
    except ExportError as exc:
        return emit({"ok": False, "error": str(exc)}, 1)
    except KeyboardInterrupt:
        return emit({"ok": False, "error": "interrupted"}, 130)


if __name__ == "__main__":
    sys.exit(main())
