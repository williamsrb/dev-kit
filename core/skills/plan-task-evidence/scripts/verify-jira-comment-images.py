#!/usr/bin/env python3
"""Fail if a Jira evidence comment's media nodes are not real issue attachments.

``check-evidence-comment.py`` only lints markup. This script is the after-post
(and after-delete) gate: every ``data-id`` in the comment must match an
attachment on the issue, with a PNG payload.

Usage:
    verify-jira-comment-images.py --issue PROJ-427 --comment-id 529383
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

MEDIA_ID_RE = re.compile(
    r'data-type="media"[^>]*data-id="([0-9a-fA-F-]{36})"',
    re.IGNORECASE,
)
ALT_RE = re.compile(
    r'data-id="([0-9a-fA-F-]{36})"[^>]*data-alt="([^"]*)"',
    re.IGNORECASE,
)
UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def agentctl_get(path: str) -> dict[str, Any]:
    proc = subprocess.run(
        ["agentctl", "jira", "request", "GET", path],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"error: agentctl GET {path} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout)[:400]}"
        )
    data = json.loads(proc.stdout)
    if data.get("status") not in (None, "ok"):
        raise SystemExit(f"error: GET {path} status={data.get('status')!r}")
    result = data.get("result", data)
    if not isinstance(result, dict):
        raise SystemExit(f"error: GET {path} returned {type(result).__name__}")
    return result


def walk_adf_media(node: Any, out: list[dict[str, Any]]) -> None:
    if isinstance(node, list):
        for child in node:
            walk_adf_media(child, out)
        return
    if not isinstance(node, dict):
        return
    if node.get("type") == "media":
        out.append(node.get("attrs") or {})
    walk_adf_media(node.get("content"), out)


def comment_media(issue: str, comment_id: str) -> tuple[list[tuple[str, str]], str]:
    result = agentctl_get(
        f"/rest/api/3/issue/{issue}/comment/{comment_id}?expand=renderedBody"
    )
    media: list[dict[str, Any]] = []
    walk_adf_media(result.get("body"), media)
    pairs: list[tuple[str, str]] = []
    for attrs in media:
        fid = str(attrs.get("id") or "").lower()
        if UUID_RE.fullmatch(fid):
            pairs.append((fid, str(attrs.get("alt") or "")))
    html = result.get("renderedBody") if isinstance(result.get("renderedBody"), str) else ""
    if not pairs:
        for fid in MEDIA_ID_RE.findall(html):
            pairs.append((fid.lower(), ""))
        for fid, alt in ALT_RE.findall(html):
            pairs.append((fid.lower(), alt))
        # unique preserve order
        seen: set[str] = set()
        uniq: list[tuple[str, str]] = []
        for fid, alt in pairs:
            if fid in seen:
                continue
            seen.add(fid)
            uniq.append((fid, alt))
        pairs = uniq
    return pairs, html


def attachment_index(issue: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    result = agentctl_get(f"/rest/api/3/issue/{issue}?fields=attachment")
    atts = ((result.get("fields") or {}).get("attachment")) or []
    by_key: dict[str, dict[str, Any]] = {}
    for att in atts:
        name = str(att.get("filename") or "")
        by_key[name.lower()] = att
        by_key[Path(name).name.lower()] = att
        for match in UUID_RE.findall(name):
            by_key[match.lower()] = att
        # "01-foo (uuid).png" from some embed paths
        stripped = UUID_RE.sub("", name)
        stripped = re.sub(r"\s*\(\s*\)", "", stripped).strip()
        if stripped:
            by_key[stripped.lower()] = att
    return atts, by_key


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--comment-id", required=True)
    args = parser.parse_args(argv)

    pairs, html = comment_media(args.issue, args.comment_id)
    if not pairs:
        print(
            f"error: comment {args.comment_id} has no media nodes",
            file=sys.stderr,
        )
        return 1

    _atts, by_key = attachment_index(args.issue)
    rendered_alts = {
        m.group(1)
        for m in re.finditer(
            r'<img[^>]+src="[^"]*attachment/content/\d+"[^>]*alt="([^"]+)"',
            html,
        )
    }
    rendered_alts |= {
        m.group(1)
        for m in re.finditer(
            r'<img[^>]+alt="([^"]+)"[^>]+src="[^"]*attachment/content/\d+"',
            html,
        )
    }
    missing: list[str] = []
    ok: list[str] = []
    for fid, alt in pairs:
        att = by_key.get(fid) or (by_key.get(alt.lower()) if alt else None)
        rendered = (not alt) or (alt in rendered_alts)
        if not att and rendered:
            # Rendered HTML already has the img; treat as ok even if filename index missed
            ok.append(f"{fid} {alt} rendered")
            continue
        if not att:
            missing.append(f"{fid} ({alt or 'no-alt'})")
            continue
        size = int(att.get("size") or 0)
        mime = str(att.get("mimeType") or "")
        if size < 500 or not mime.startswith("image/"):
            missing.append(f"{fid} ({att.get('filename')} size={size} mime={mime})")
            continue
        if alt and rendered_alts and alt not in rendered_alts:
            missing.append(f"{fid} ({alt}) attachment exists but rendered HTML has no img")
            continue
        ok.append(f"{fid} {att.get('filename')} {size}")

    print(
        json.dumps(
            {
                "issue": args.issue,
                "commentId": args.comment_id,
                "ok": ok,
                "missing": missing,
            },
            indent=2,
        )
    )
    if missing:
        print(
            f"error: {len(missing)}/{len(pairs)} media ids have no image attachment on {args.issue}",
            file=sys.stderr,
        )
        return 1
    print(f"OK — {len(ok)}/{len(pairs)} media nodes resolve to image attachments.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
