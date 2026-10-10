#!/usr/bin/env python3
"""Drive image-to-disk over real stdio JSON-RPC and assert on the wire format."""

import base64
import json
import os
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

SERVER = "${HOME}/.agents/mcp/image-to-disk/server.py"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
)
MODERN = "2026-07-28"
META = {
    "io.modelcontextprotocol/protocolVersion": MODERN,
    "io.modelcontextprotocol/clientInfo": {"name": "harness", "version": "1.0"},
    "io.modelcontextprotocol/clientCapabilities": {},
}

failures = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{'' if cond else f'  <- {detail}'}")
    if not cond:
        failures.append(name)


class Client:
    def __init__(self, outdir, roots):
        env = {**os.environ, "IMAGE_TO_DISK_DIR": str(outdir),
               "IMAGE_TO_DISK_ROOTS": roots}
        self.proc = subprocess.Popen(
            [sys.executable, SERVER], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=env, bufsize=1,
        )
        self.n = 0

    def call(self, method, params=None, meta=META):
        self.n += 1
        params = dict(params or {})
        if meta is not None:
            params["_meta"] = meta
        msg = {"jsonrpc": "2.0", "id": self.n, "method": method, "params": params}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)


def serve_http(directory):
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def main():
    tmp = Path(tempfile.mkdtemp(prefix="img2disk-"))
    outdir, web = tmp / "out", tmp / "web"
    web.mkdir(parents=True)
    (web / "logo.png").write_bytes(PNG)
    httpd, port = serve_http(web)

    c = Client(outdir, str(outdir))

    print("\n--- protocol: 2026-07-28 (stateless) ---")
    r = c.call("server/discover")["result"]
    check("discover resultType=complete", r.get("resultType") == "complete", r)
    check("discover advertises 2026-07-28", MODERN in r.get("supportedVersions", []), r)
    check("discover carries serverInfo in _meta",
          r.get("_meta", {}).get("io.modelcontextprotocol/serverInfo", {}).get("name")
          == "image-to-disk", r.get("_meta"))
    check("discover is cacheable", r.get("ttlMs") and r.get("cacheScope") == "public", r)
    check("discover declares tools capability", "tools" in r.get("capabilities", {}), r)

    r = c.call("tools/list")["result"]
    names = [t["name"] for t in r["tools"]]
    check("tools/list resultType", r.get("resultType") == "complete", r.keys())
    check("tools/list cacheable", r.get("ttlMs") and r.get("cacheScope"), r.keys())
    check("4 tools listed", len(names) == 4, names)
    check("tools/list order is deterministic",
          [t["name"] for t in c.call("tools/list")["result"]["tools"]] == names)

    print("\n--- version negotiation ---")
    e = c.call("tools/list", meta={**META,
               "io.modelcontextprotocol/protocolVersion": "1900-01-01"})["error"]
    check("unsupported version -> -32022", e["code"] == -32022, e)
    check("error lists supported versions", MODERN in e["data"]["supported"], e)
    check("error echoes requested", e["data"]["requested"] == "1900-01-01", e)

    e = c.call("tools/list", meta={"io.modelcontextprotocol/protocolVersion": MODERN})
    check("missing clientCapabilities -> -32602", e["error"]["code"] == -32602, e)

    print("\n--- saving images ---")
    r = c.call("tools/call", {"name": "save_image_from_url",
                              "arguments": {"url": f"http://127.0.0.1:{port}/logo.png"}})["result"]
    saved = Path(r["structuredContent"]["path"])
    check("http url saved", saved.is_file() and saved.read_bytes() == PNG, r)
    check("png detected", r["structuredContent"]["media_type"] == "image/png", r)
    check("filename from url stem", "logo" in saved.name, saved.name)
    check("landed in output dir", saved.parent == outdir, saved)
    check("isError false", r["isError"] is False, r)
    check("tools/call resultType", r.get("resultType") == "complete", r.keys())

    data_uri = "data:image/png;base64," + base64.b64encode(PNG).decode()
    r = c.call("tools/call", {"name": "save_image_from_base64",
                              "arguments": {"data": data_uri, "path": "shot.png"}})["result"]
    p = Path(r["structuredContent"]["path"])
    check("data uri saved", p.read_bytes() == PNG, r)
    check("relative path -> output dir", p == outdir / "shot.png", p)

    r = c.call("tools/call", {"name": "save_image_from_base64",
                              "arguments": {"data": data_uri, "path": "shot.png"}})["result"]
    check("no clobber by default", Path(r["structuredContent"]["path"]).name == "shot-1.png", r)

    r = c.call("tools/call", {"name": "save_image_from_base64",
                              "arguments": {"data": data_uri, "path": "shot.png",
                                            "overwrite": True}})["result"]
    check("overwrite honoured", Path(r["structuredContent"]["path"]).name == "shot.png", r)

    r = c.call("tools/call", {"name": "save_image_from_url",
                              "arguments": {"url": f"file://{web}/logo.png",
                                            "path": "sub/dir/copy"}})["result"]
    p = Path(r["structuredContent"]["path"])
    check("file:// url saved", p.read_bytes() == PNG, r)
    check("extension inferred", p.name == "copy.png", p)
    check("nested dirs created", p.parent == outdir / "sub" / "dir", p)

    svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'
    r = c.call("tools/call", {"name": "save_text_file",
                              "arguments": {"text": svg, "path": "vec.svg"}})["result"]
    check("svg sniffed", r["structuredContent"]["media_type"] == "image/svg+xml", r)

    print("\n--- guardrails ---")
    r = c.call("tools/call", {"name": "save_image_from_base64",
                              "arguments": {"data": data_uri,
                                            "path": "../../escape.png"}})["result"]
    check("traversal blocked", r["isError"] is True, r)
    check("traversal not written", not (tmp / "escape.png").exists())
    check("guardrail is a tool error, not a crash",
          "outside the allowed roots" in r["content"][0]["text"], r)

    r = c.call("tools/call", {"name": "save_image_from_base64",
                              "arguments": {"data": "!!!not base64!!!"}})["result"]
    check("bad base64 -> isError", r["isError"] is True, r)

    r = c.call("tools/call", {"name": "save_image_from_url",
                              "arguments": {"url": f"http://127.0.0.1:{port}/nope.png"}})["result"]
    check("404 -> isError", r["isError"] is True and "404" in r["content"][0]["text"], r)

    r = c.call("tools/call", {"name": "save_image_from_url",
                              "arguments": {"url": "ftp://example.com/x.png"}})["result"]
    check("bad scheme -> isError", r["isError"] is True, r)

    e = c.call("tools/call", {"name": "no_such_tool", "arguments": {}})
    check("unknown tool -> -32602", e["error"]["code"] == -32602, e)

    r = c.call("tools/call", {"name": "list_output_dir", "arguments": {}})["result"]
    listed = {x["name"] for x in r["structuredContent"]["entries"]}
    check("list_output_dir sees writes", "shot.png" in listed, listed)

    print("\n--- statelessness ---")
    fresh = Client(outdir, str(outdir))
    r = fresh.call("tools/call", {"name": "save_image_from_base64",
                                  "arguments": {"data": data_uri, "path": "cold.png"}})["result"]
    check("first request needs no handshake", r.get("isError") is False, r)
    fresh.close()

    print("\n--- legacy client (initialize handshake) ---")
    old = Client(outdir, str(outdir))
    r = old.call("initialize", {"protocolVersion": "2025-06-18",
                                "capabilities": {}, "clientInfo": {"name": "old", "version": "1"}},
                 meta=None)["result"]
    check("initialize answered", r["protocolVersion"] == "2025-06-18", r)
    check("initialize returns serverInfo", r["serverInfo"]["name"] == "image-to-disk", r)
    r = old.call("tools/list", meta=None)["result"]
    check("legacy tools/list works", len(r["tools"]) == 4, r.keys())
    check("legacy result omits resultType", "resultType" not in r, r.keys())
    r = old.call("tools/call", {"name": "save_image_from_base64",
                                "arguments": {"data": data_uri, "path": "legacy.png"}},
                 meta=None)["result"]
    check("legacy tools/call works", r["isError"] is False, r)
    old.close()

    c.close()
    httpd.shutdown()

    print(f"\n{'ALL PASS' if not failures else 'FAILURES: ' + ', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
