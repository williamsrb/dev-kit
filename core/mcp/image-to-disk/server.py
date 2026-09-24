#!/usr/bin/env python3
"""image-to-disk — a stateless MCP server that writes images (and text) to disk.

Bridges tools that can *see* an image but not *save* it (e.g. the in-app Browser
pane) to the local filesystem. Two ingest paths:

  save_image_from_url     server downloads the URL itself (http/https/file/data)
  save_image_from_base64  caller passes a data: URI or raw base64 payload

Protocol
--------
Speaks MCP revision 2026-07-28, which is a *stateless* protocol: there is no
`initialize` handshake and no session. Every request carries its own protocol
version and client capabilities in `_meta`, and each request is processed
independently. `server/discover` advertises supported versions and identity.

The server is dual-era: a request carrying per-request `_meta` is served under
2026-07-28 semantics, while an `initialize` request selects legacy semantics for
clients that still expect the handshake (2025-11-25 and earlier). Legacy mode is
scoped to this stdio process, as the spec permits.

Statelessness is honoured at the tool layer too: no handles, no server-side
context — each call carries everything needed to perform the write.

Stdlib only (Python 3.12) — no MCP SDK, no pip install. JSON-RPC 2.0 over
stdin/stdout, one message per line. Never write to stdout except responses;
diagnostics go to stderr (the spec's recommended replacement for the now
deprecated logging feature on stdio).

Configuration (environment):
  IMAGE_TO_DISK_DIR     default output directory
                        (default: ~/Pictures/claude-captures)
  IMAGE_TO_DISK_ROOTS   colon-separated write roots; paths outside them are
                        rejected (default: the output dir + the server's cwd)
  IMAGE_TO_DISK_MAX_MB  max payload size in MiB (default: 64)
  IMAGE_TO_DISK_STRICT  "0" to accept modern requests that omit required
                        `_meta` fields instead of rejecting them (default: on)
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SERVER_NAME = "image-to-disk"
SERVER_VERSION = "1.0.0"
IMPLEMENTATION = {"name": SERVER_NAME, "version": SERVER_VERSION}

# Revisions using per-request metadata (stateless, no handshake).
MODERN_VERSIONS = ("2026-07-28",)
# Revisions using the initialize handshake, still accepted for compatibility.
LEGACY_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
ALL_VERSIONS = MODERN_VERSIONS + LEGACY_VERSIONS

META_PROTOCOL_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CLIENT_CAPABILITIES = "io.modelcontextprotocol/clientCapabilities"
META_CLIENT_INFO = "io.modelcontextprotocol/clientInfo"
META_SERVER_INFO = "io.modelcontextprotocol/serverInfo"

# JSON-RPC error codes. -32020..-32099 is the MCP-reserved sub-range.
INVALID_PARAMS = -32602
METHOD_NOT_FOUND = -32601
UNSUPPORTED_PROTOCOL_VERSION = -32022

# The tool list is static, so it is safe for clients to cache it.
TOOLS_TTL_MS = 3_600_000
DISCOVER_TTL_MS = 3_600_000

CAPABILITIES = {"tools": {"listChanged": False}}

INSTRUCTIONS = (
    "Saves images to disk on behalf of tools that can display but not write "
    "them, such as a browser pane. Prefer save_image_from_url so image bytes "
    "are fetched server-side and never pass through the conversation; fall "
    "back to save_image_from_base64 for inline data: payloads."
)

STRICT_META = os.environ.get("IMAGE_TO_DISK_STRICT", "1") not in ("0", "false", "no")

DEFAULT_DIR = Path(
    os.environ.get("IMAGE_TO_DISK_DIR") or Path.home() / "Pictures" / "claude-captures"
).expanduser()

_roots_env = os.environ.get("IMAGE_TO_DISK_ROOTS")
if _roots_env:
    WRITE_ROOTS = [Path(p).expanduser().resolve() for p in _roots_env.split(":") if p]
else:
    WRITE_ROOTS = [DEFAULT_DIR.resolve(), Path.cwd().resolve()]

MAX_BYTES = int(float(os.environ.get("IMAGE_TO_DISK_MAX_MB", "64")) * 1024 * 1024)
FETCH_TIMEOUT = 30
USER_AGENT = f"{SERVER_NAME}/{SERVER_VERSION}"

DATA_URI_RE = re.compile(r"^data:([^;,]*)((?:;[^;,]+)*),", re.IGNORECASE)

# Set when a client opens with `initialize`; scoped to this process, which is
# what the spec allows for legacy semantics on stdio.
LEGACY_MODE = False


class ToolError(Exception):
    """Expected failure; reported to the client as an isError tool result."""


class ProtocolError(Exception):
    """Malformed or unsupported request; reported as a JSON-RPC error."""

    def __init__(self, code: int, message: str, data: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def log(msg: str) -> None:
    print(f"[{SERVER_NAME}] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Content sniffing
# --------------------------------------------------------------------------- #

MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"GIF87a", "image/gif", ".gif"),
    (b"GIF89a", "image/gif", ".gif"),
    (b"BM", "image/bmp", ".bmp"),
    (b"\x00\x00\x01\x00", "image/x-icon", ".ico"),
    (b"II*\x00", "image/tiff", ".tiff"),
    (b"MM\x00*", "image/tiff", ".tiff"),
    (b"%PDF-", "application/pdf", ".pdf"),
)

EXT_BY_MEDIA = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    "image/tiff": ".tiff",
    "application/pdf": ".pdf",
}


def sniff(data: bytes) -> tuple[str, str]:
    """Return (media_type, extension) for a byte payload."""
    for magic, media, ext in MAGIC:
        if data.startswith(magic):
            return media, ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    if data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"avif", b"avis"):
            return "image/avif", ".avif"
        if brand in (b"heic", b"heix", b"mif1", b"heim"):
            return "image/heic", ".heic"
    head = data[:512].lstrip()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:2048]):
        return "image/svg+xml", ".svg"
    return "application/octet-stream", ".bin"


# --------------------------------------------------------------------------- #
# Path resolution
# --------------------------------------------------------------------------- #


def _inside_roots(target: Path) -> bool:
    return any(target == root or root in target.parents for root in WRITE_ROOTS)


def resolve_target(path: str | None, ext: str, stem_hint: str | None = None) -> Path:
    """Turn the caller's `path` into a concrete, validated file path.

    `path` may be absolute or relative (resolved against the default dir), and
    may name a directory (a filename is then generated) or a file. A missing
    extension is filled in from the sniffed content type.
    """
    if path:
        candidate = Path(path).expanduser()
        treat_as_dir = path.endswith(("/", os.sep)) or (
            candidate.exists() and candidate.is_dir()
        )
        if not candidate.is_absolute():
            candidate = DEFAULT_DIR / candidate
    else:
        candidate = DEFAULT_DIR
        treat_as_dir = True

    if treat_as_dir:
        candidate = candidate / (generated_name(stem_hint) + ext)
    elif not candidate.suffix:
        candidate = candidate.with_name(candidate.name + ext)

    # Resolve symlinks on the existing prefix so `..` and links cannot escape.
    resolved = Path(os.path.normpath(candidate.absolute()))
    anchor = resolved.parent
    while not anchor.exists() and anchor != anchor.parent:
        anchor = anchor.parent
    resolved = anchor.resolve() / resolved.relative_to(anchor)

    if not _inside_roots(resolved):
        allowed = ", ".join(str(r) for r in WRITE_ROOTS)
        raise ToolError(
            f"refusing to write outside the allowed roots: {resolved}\n"
            f"allowed roots: {allowed}\n"
            f"(set IMAGE_TO_DISK_ROOTS to widen them)"
        )
    return resolved


def generated_name(stem_hint: str | None = None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if stem_hint:
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", stem_hint).strip("-.")[:60]
        if slug:
            return f"{stamp}-{slug}"
    return f"{stamp}-image"


def unique_path(target: Path) -> Path:
    if not target.exists():
        return target
    stem, suffix, parent = target.stem, target.suffix, target.parent
    for n in range(1, 1000):
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
    raise ToolError(f"could not find a free filename next to {target}")


def write_bytes(data: bytes, path: str | None, overwrite: bool, stem_hint: str | None,
                media_hint: str | None = None) -> dict:
    if not data:
        raise ToolError("empty payload — nothing to write")
    if len(data) > MAX_BYTES:
        raise ToolError(
            f"payload is {len(data) / 1048576:.1f} MiB, over the "
            f"{MAX_BYTES / 1048576:.0f} MiB limit (raise IMAGE_TO_DISK_MAX_MB)"
        )

    media, ext = sniff(data)
    if media == "application/octet-stream" and media_hint:
        media = media_hint
        ext = EXT_BY_MEDIA.get(media_hint.lower(), ext)

    target = resolve_target(path, ext, stem_hint)
    target = target if overwrite else unique_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

    return {
        "path": str(target),
        "bytes": len(data),
        "media_type": media,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


# --------------------------------------------------------------------------- #
# Payload decoding / fetching
# --------------------------------------------------------------------------- #


def b64decode(text: str) -> bytes:
    cleaned = re.sub(r"\s+", "", text).replace("-", "+").replace("_", "/")
    cleaned += "=" * (-len(cleaned) % 4)
    try:
        return base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ToolError(f"payload is not valid base64: {exc}") from exc


def decode_payload(payload: str) -> tuple[bytes, str | None]:
    """Decode a data: URI or a bare base64 string into (bytes, media_hint)."""
    payload = payload.strip()
    match = DATA_URI_RE.match(payload)
    if match:
        media = (match.group(1) or "").lower() or None
        params = (match.group(2) or "").lower()
        body = payload[match.end():]
        if ";base64" in params:
            return b64decode(body), media
        return urllib.parse.unquote_to_bytes(body), media
    return b64decode(payload), None


def fetch(url: str) -> tuple[bytes, str | None]:
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme == "data":
        return decode_payload(url)

    if scheme == "file":
        source = Path(urllib.parse.unquote(parsed.path))
        if not source.is_file():
            raise ToolError(f"no such file: {source}")
        return source.read_bytes(), None

    if scheme not in ("http", "https"):
        raise ToolError(
            f"unsupported URL scheme {scheme!r} — use http, https, file or data"
        )

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT) as response:
            data = response.read(MAX_BYTES + 1)
            media = (response.headers.get_content_type() or "").lower() or None
    except urllib.error.HTTPError as exc:
        raise ToolError(f"HTTP {exc.code} {exc.reason} fetching {url}") from exc
    except urllib.error.URLError as exc:
        raise ToolError(f"could not fetch {url}: {exc.reason}") from exc
    except OSError as exc:
        raise ToolError(f"could not fetch {url}: {exc}") from exc

    if len(data) > MAX_BYTES:
        raise ToolError(
            f"response exceeds the {MAX_BYTES / 1048576:.0f} MiB limit "
            f"(raise IMAGE_TO_DISK_MAX_MB)"
        )
    return data, media


def url_stem(url: str) -> str | None:
    stem = Path(Path(urllib.parse.urlparse(url).path).name).stem
    return stem or None


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #

PATH_DESC = (
    "Destination. Absolute path, or relative to the default output directory. "
    "May be a directory (trailing slash) to auto-name the file. A missing "
    "extension is filled in from the detected image type."
)

SAVE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Absolute path actually written."},
        "bytes": {"type": "integer", "description": "Size of the file on disk."},
        "media_type": {"type": "string", "description": "Detected media type."},
        "sha256": {"type": "string", "description": "SHA-256 of the file contents."},
        "source": {"type": "string", "description": "Origin URL, when applicable."},
    },
    "required": ["path", "bytes", "media_type", "sha256"],
}

# Deterministic order: the spec asks servers to keep tools/list stable so
# clients can cache it and prompt caches stay warm.
TOOLS = [
    {
        "name": "save_image_from_url",
        "title": "Save image from URL",
        "description": (
            "Download an image and write it to disk. The server fetches the URL "
            "itself, so image bytes never pass through the conversation. Accepts "
            "http(s), file: and data: URLs. Use this for images visible in a "
            "browser page — read the element's src and pass it here. Note the "
            "server has no browser session cookies; for auth-gated images, have "
            "the page produce a data: URL and use save_image_from_base64."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Image URL to download."},
                "path": {"type": "string", "description": PATH_DESC},
                "overwrite": {
                    "type": "boolean",
                    "description": "Overwrite an existing file. Default false — "
                                   "a numeric suffix is added instead.",
                    "default": False,
                },
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        "outputSchema": SAVE_OUTPUT_SCHEMA,
        "annotations": {"readOnlyHint": False, "destructiveHint": False,
                        "idempotentHint": False, "openWorldHint": True},
    },
    {
        "name": "save_image_from_base64",
        "title": "Save inline image",
        "description": (
            "Write an inline image to disk from a data: URI or a raw base64 "
            "string — canvas.toDataURL() output, an inlined <img src=\"data:...\">, "
            "or a generated SVG. Prefer save_image_from_url when a fetchable URL "
            "exists: it keeps the payload out of the conversation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "string",
                    "description": "A data: URI or bare base64 payload.",
                },
                "path": {"type": "string", "description": PATH_DESC},
                "overwrite": {"type": "boolean", "default": False},
            },
            "required": ["data"],
            "additionalProperties": False,
        },
        "outputSchema": SAVE_OUTPUT_SCHEMA,
        "annotations": {"readOnlyHint": False, "destructiveHint": False,
                        "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "save_text_file",
        "title": "Save text file",
        "description": (
            "Write UTF-8 text to disk under the same roots — for SVG markup, "
            "HTML snapshots or notes captured alongside an image."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "File contents."},
                "path": {"type": "string", "description": PATH_DESC},
                "overwrite": {"type": "boolean", "default": False},
            },
            "required": ["text", "path"],
            "additionalProperties": False,
        },
        "outputSchema": SAVE_OUTPUT_SCHEMA,
        "annotations": {"readOnlyHint": False, "destructiveHint": False,
                        "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "list_output_dir",
        "title": "List saved files",
        "description": (
            "List files in the output directory (or a subdirectory) to confirm "
            "what was written. Returns name, size and modification time."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "subdir": {
                    "type": "string",
                    "description": "Optional path relative to the default output "
                                   "directory, or an absolute path inside a root.",
                }
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": False},
    },
]


def require_str(args: dict, key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"`{key}` is required and must be a non-empty string")
    return value


def summary(verb: str, result: dict) -> str:
    return (
        f"{verb} {result['path']} ({result['bytes']} bytes, {result['media_type']})"
    )


def tool_save_image_from_url(args: dict) -> tuple[str, dict]:
    url = require_str(args, "url")
    data, media = fetch(url)
    result = write_bytes(
        data, args.get("path"), bool(args.get("overwrite")), url_stem(url), media
    )
    result["source"] = url
    return summary("Saved", result), result


def tool_save_image_from_base64(args: dict) -> tuple[str, dict]:
    data, media = decode_payload(require_str(args, "data"))
    result = write_bytes(data, args.get("path"), bool(args.get("overwrite")), None, media)
    return summary("Saved", result), result


def tool_save_text_file(args: dict) -> tuple[str, dict]:
    text = args.get("text")
    if not isinstance(text, str):
        raise ToolError("`text` is required and must be a string")
    result = write_bytes(
        text.encode("utf-8"), require_str(args, "path"), bool(args.get("overwrite")), None
    )
    return summary("Wrote", result), result


def tool_list_output_dir(args: dict) -> tuple[str, dict]:
    subdir = args.get("subdir")
    base = Path(subdir).expanduser() if subdir else DEFAULT_DIR
    if not base.is_absolute():
        base = DEFAULT_DIR / base
    base = Path(os.path.normpath(base.absolute()))
    if not _inside_roots(base):
        raise ToolError(f"{base} is outside the allowed roots")
    if not base.is_dir():
        return f"{base} does not exist yet.", {"dir": str(base), "entries": []}

    entries = []
    for item in sorted(base.iterdir(), key=lambda p: p.name):
        stat = item.stat()
        entries.append({
            "name": item.name + ("/" if item.is_dir() else ""),
            "bytes": stat.st_size,
            "modified": datetime.fromtimestamp(
                stat.st_mtime, timezone.utc
            ).isoformat(timespec="seconds"),
        })
    lines = [f"{base} ({len(entries)} entries)"]
    lines += [f"  {e['name']}  {e['bytes']}B  {e['modified']}" for e in entries]
    return "\n".join(lines), {"dir": str(base), "entries": entries}


HANDLERS = {
    "save_image_from_url": tool_save_image_from_url,
    "save_image_from_base64": tool_save_image_from_base64,
    "save_text_file": tool_save_text_file,
    "list_output_dir": tool_list_output_dir,
}


# --------------------------------------------------------------------------- #
# JSON-RPC plumbing
# --------------------------------------------------------------------------- #


def negotiate(method: str, params: dict) -> bool:
    """Validate per-request protocol metadata; return True for modern requests.

    Under 2026-07-28 there is no handshake, so every request declares its own
    version and capabilities. A request that declares neither is treated as
    legacy, which is how a dual-era server disambiguates the two eras.
    """
    meta = params.get("_meta")
    meta = meta if isinstance(meta, dict) else {}
    requested = meta.get(META_PROTOCOL_VERSION)

    if requested is None:
        # `server/discover` is a modern-only method, so answer it in modern
        # shape even when a probing client omits the metadata.
        return method == "server/discover" and not LEGACY_MODE

    if requested not in ALL_VERSIONS:
        raise ProtocolError(
            UNSUPPORTED_PROTOCOL_VERSION,
            "Unsupported protocol version",
            {"supported": list(ALL_VERSIONS), "requested": requested},
        )

    if STRICT_META and META_CLIENT_CAPABILITIES not in meta:
        raise ProtocolError(
            INVALID_PARAMS,
            f"missing required `_meta` field {META_CLIENT_CAPABILITIES!r} "
            f"(set IMAGE_TO_DISK_STRICT=0 to accept requests without it)",
        )

    return requested in MODERN_VERSIONS


def make_result(body: dict, modern: bool, ttl_ms: int | None = None) -> dict:
    """Add the fields the modern revision requires to a result body."""
    if not modern:
        return body
    result = {"resultType": "complete", **body}
    if ttl_ms is not None:
        result.setdefault("ttlMs", ttl_ms)
        result.setdefault("cacheScope", "public")
    result.setdefault("_meta", {})[META_SERVER_INFO] = IMPLEMENTATION
    return result


def call_tool(params: dict, modern: bool) -> dict:
    name = params.get("name")
    handler = HANDLERS.get(name)
    if handler is None:
        raise ProtocolError(INVALID_PARAMS, f"Unknown tool: {name}")

    try:
        text, structured = handler(params.get("arguments") or {})
    except ToolError as exc:
        return make_result(
            {"content": [{"type": "text", "text": str(exc)}], "isError": True}, modern
        )
    except Exception as exc:  # unexpected — surface it rather than dying
        log(f"tool {name} failed: {exc!r}")
        return make_result(
            {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}],
             "isError": True},
            modern,
        )

    return make_result(
        {
            "content": [{"type": "text", "text": text}],
            "structuredContent": structured,
            "isError": False,
        },
        modern,
    )


def handle(message: dict) -> dict | None:
    global LEGACY_MODE

    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}

    try:
        modern = negotiate(method, params)
    except ProtocolError as exc:
        return err(msg_id, exc.code, exc.message, exc.data)

    try:
        if method == "server/discover":
            # A modern-only method: always answered in modern shape, so a
            # dual-era client's probe gets a DiscoverResult it can recognise.
            return ok(msg_id, make_result(
                {
                    "supportedVersions": list(ALL_VERSIONS),
                    "capabilities": CAPABILITIES,
                    "instructions": INSTRUCTIONS,
                },
                modern=True,
                ttl_ms=DISCOVER_TTL_MS,
            ))

        if method == "initialize":
            # Legacy handshake. Echo a version the client asked for when we
            # support it, otherwise our newest legacy revision.
            LEGACY_MODE = True
            requested = params.get("protocolVersion")
            version = requested if requested in ALL_VERSIONS else LEGACY_VERSIONS[0]
            log(f"legacy client connected, serving protocol {version}")
            return ok(msg_id, {
                "protocolVersion": version,
                "capabilities": CAPABILITIES,
                "serverInfo": IMPLEMENTATION,
                "instructions": INSTRUCTIONS,
            })

        if method in ("notifications/initialized", "notifications/cancelled"):
            return None

        if method == "ping":
            # Removed in 2026-07-28; still answered for legacy clients.
            return ok(msg_id, make_result({}, modern))

        if method == "tools/list":
            return ok(msg_id, make_result({"tools": TOOLS}, modern, TOOLS_TTL_MS))

        if method == "tools/call":
            return ok(msg_id, call_tool(params, modern))

    except ProtocolError as exc:
        return err(msg_id, exc.code, exc.message, exc.data)

    if msg_id is None:
        return None
    return err(msg_id, METHOD_NOT_FOUND, f"Method not found: {method}")


def ok(msg_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def err(msg_id, code: int, message: str, data: dict | None = None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": error}


def emit(response: dict) -> None:
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def serve() -> None:
    log(
        f"ready — protocol {MODERN_VERSIONS[0]} (stateless), "
        f"output dir {DEFAULT_DIR}, roots {[str(r) for r in WRITE_ROOTS]}"
    )
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            log(f"bad JSON: {exc}")
            continue
        if isinstance(message, list):
            for response in (handle(m) for m in message):
                if response is not None:
                    emit(response)
            continue
        response = handle(message)
        if response is not None:
            emit(response)


if __name__ == "__main__":
    try:
        serve()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
