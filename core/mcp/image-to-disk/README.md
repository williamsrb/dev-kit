# image-to-disk

A stateless MCP server that writes images to disk — the bridge for tools that
can *display* an image but not *save* it (the in-app Browser pane, page canvases,
inline `data:` images).

Stdlib-only Python 3.12. No MCP SDK, no `pip install`, no dependencies.

## Why the tools take a source, not a picture

A screenshot the browser hands the model lives in the model's context, not on
disk, and those bytes cannot be cheaply re-emitted into a tool call. So the
bridge takes the image's *origin* and does the retrieval itself:

- `save_image_from_url` — the server downloads it. Image bytes never pass
  through the conversation. **Prefer this.**
- `save_image_from_base64` — for genuinely inline payloads (`canvas.toDataURL()`,
  `<img src="data:...">`, generated SVG). The payload does pass through context,
  so it costs tokens proportional to the image.

## Tools

| Tool | Purpose |
| --- | --- |
| `save_image_from_url` | Download `http(s)://`, `file://` or `data:` URL to disk |
| `save_image_from_base64` | Write a `data:` URI or bare base64 payload to disk |
| `save_text_file` | Write UTF-8 text (SVG markup, HTML snapshots, notes) |
| `list_output_dir` | List what was written, with sizes and timestamps |

All four accept `path`: absolute, or relative to the output directory, or a
directory (trailing slash) to auto-name the file. A missing extension is filled
in from the detected media type — content is sniffed by magic bytes, not
trusted from the URL or the declared MIME type.

Writes never clobber by default; a `-1`, `-2` … suffix is added unless you pass
`overwrite: true`.

## Install

Shared installer (Claude):

```bash
python3 ${HOME}/.agents/mcp/install.py install image-to-disk
```

Or Claude Code only:

```bash
claude mcp add image-to-disk -s user -- python3 ${HOME}/.agents/mcp/image-to-disk/server.py
```

Then restart Claude Code. Verify with `claude mcp list`.

To pin the output directory and the roots it may write to:

```bash
claude mcp add image-to-disk -s user -e IMAGE_TO_DISK_DIR=$HOME/Pictures/claude-captures -e IMAGE_TO_DISK_ROOTS=$HOME/Pictures:$HOME/Workspace -- python3 ${HOME}/.agents/mcp/image-to-disk/server.py
```

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `IMAGE_TO_DISK_DIR` | `~/Pictures/claude-captures` | Default output directory |
| `IMAGE_TO_DISK_ROOTS` | output dir + server cwd | Colon-separated roots; writes outside are refused |
| `IMAGE_TO_DISK_MAX_MB` | `64` | Max payload size |
| `IMAGE_TO_DISK_STRICT` | on | `0` accepts modern requests missing required `_meta` |

## Typical browser flow

1. `read_page` or `find` to locate the image element.
2. Read its `src` (via `javascript_tool` if it isn't in the accessibility tree).
3. `save_image_from_url` with that `src`.

The server has no browser session cookies, so an auth-gated image will 401/403.
Fall back to having the page itself produce the bytes:

```js
// in javascript_tool — returns a data: URL for save_image_from_base64
const r = await fetch(imgSrc);
const b = await r.blob();
await new Promise(res => { const f = new FileReader(); f.onload = () => res(f.result); f.readAsDataURL(b); });
```

## Protocol

Implements MCP revision **2026-07-28**, which is a stateless protocol: no
`initialize` handshake, no session. Every request carries its own protocol
version and client capabilities in `_meta`; every result carries `resultType`
and the server identity in `_meta`. `server/discover` advertises supported
versions, capabilities and identity, and doubles as the stdio backward-
compatibility probe.

The server is **dual-era**. A request carrying per-request `_meta` is served
under 2026-07-28 semantics; an `initialize` request selects legacy semantics
(2025-11-25 and earlier) for clients that still expect the handshake, scoped to
the stdio process. Both eras are exercised by the test suite — drop the legacy
branch in `handle()` once every client you use speaks the modern revision.

Statelessness holds at the tool layer too: no handles, no server-side context,
each call self-contained.

## Test

```bash
python3 ${HOME}/.agents/mcp/image-to-disk/test_server.py
```

Spawns the server as a real subprocess and speaks JSON-RPC over stdio: wire
format for both eras, version negotiation and the `-32022`/`-32602` errors,
every tool, and the guardrails (path traversal, bad base64, HTTP 404, unsupported
scheme, unknown tool). Writes to a temp dir; nothing touches your output
directory.
