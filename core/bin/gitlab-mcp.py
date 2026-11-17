#!/usr/bin/env python3
"""Launch gitlab-mcp-server with credentials from AGENTS_HOME/.auth, not from mcp.json.

The server reads its token only from the environment; it has no token-file
option. This wrapper supplies the environment so no client config file has to
hold the secret.

Auth file (first match), each a `tokens:` list:
  $AGENTS_HOME/.auth/gitlab-access-token.yaml   (optional fallback)
Each entry has key_name, key_value, gitlab_url, and optionally key_scope and
expires_at. The entry named by GITLAB_TOKEN_NAME is used; without it, the first
entry. gitlab_url can be replaced by GITLAB_URL in the environment.
No hardcoded GitLab host.

Python 3.12, standard library only.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path

SERVER = Path.home() / ".local" / "bin" / "gitlab-mcp-server"
AUTH_NAMES = ("gitlab-access-token.yaml",)

# The server is a third-party binary holding a GitLab PAT. It gets a built
# environment, not this process's, so an unrelated secret in the shell (AWS keys,
# other tokens) is never handed to it. Add a name here only when the server needs it.
ENV_PASSTHROUGH = (
    "PATH", "HOME", "TMPDIR", "LANG", "LC_ALL",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "no_proxy",
    "SSL_CERT_FILE", "SSL_CERT_DIR",
)

# 3.x removed the self-updater. 2.x replaced itself hourly from a single-maintainer
# GitHub repo and only this variable disabled it, so it stays set in case the
# binary is rolled back to 2.x.
AUTO_UPDATE = "false"


def agents_home() -> Path:
    raw = os.environ.get("AGENTS_HOME")
    return Path(raw) if raw else Path.home() / ".agents"


def resolve_auth_file() -> Path:
    root = agents_home() / ".auth"
    for name in AUTH_NAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return root / AUTH_NAMES[0]


def load_tokens(path: Path) -> list[dict[str, str]]:
    """Parse the `tokens:` list of flat `key: "value"` entries. Avoids a PyYAML dependency."""
    if not path.is_file():
        sys.exit(f"gitlab-mcp: missing credential file {path}")
    if path.stat().st_mode & 0o077:
        print(f"gitlab-mcp: {path} is group/world readable; chmod 600 it", file=sys.stderr)

    entries: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line == "tokens:":
            continue
        if line.startswith("-"):
            entries.append({})
            line = line[1:].strip()
        key, sep, value = line.partition(":")
        if sep and entries:
            entries[-1][key.strip()] = value.strip().strip('"').strip("'")
    return entries


def select_token(entries: list[dict[str, str]], path: Path) -> dict[str, str]:
    if not entries:
        sys.exit(f"gitlab-mcp: no `tokens:` list in {path} (flat access_token files are no longer supported)")
    wanted = os.environ.get("GITLAB_TOKEN_NAME", "")
    if not wanted:
        return entries[0]
    for entry in entries:
        if entry.get("key_name") == wanted:
            return entry
    names = ", ".join(entry.get("key_name", "?") for entry in entries)
    sys.exit(f"gitlab-mcp: no token named {wanted!r} in {path} (have: {names})")


def warn_on_expiry(expires_at: str) -> None:
    """A silently expired PAT looks like a broken server; say so on stderr instead."""
    try:
        expiry = date.fromisoformat(expires_at)
    except ValueError:
        return
    remaining = (expiry - datetime.now(UTC).date()).days
    if remaining < 0:
        print(f"gitlab-mcp: token EXPIRED on {expires_at}; calls will fail", file=sys.stderr)
    elif remaining <= 30:
        print(f"gitlab-mcp: token expires in {remaining} day(s) ({expires_at})", file=sys.stderr)


def main(argv: list[str]) -> int:
    auth_file = resolve_auth_file()
    auth = select_token(load_tokens(auth_file), auth_file)
    token = auth.get("key_value", "")
    if not token:
        sys.exit(f"gitlab-mcp: no key_value for token {auth.get('key_name', '?')!r} in {auth_file}")
    if expires_at := auth.get("expires_at", ""):
        warn_on_expiry(expires_at)
    url = auth.get("gitlab_url") or os.environ.get("GITLAB_URL") or ""
    if not url:
        sys.exit("gitlab-mcp: set gitlab_url in the auth file or GITLAB_URL in the environment")
    if not SERVER.is_file() or not os.access(SERVER, os.X_OK):
        sys.exit(f"gitlab-mcp: server binary not executable at {SERVER}")

    env = {name: os.environ[name] for name in ENV_PASSTHROUGH if name in os.environ}
    env["GITLAB_TOKEN"] = token
    env["GITLAB_URL"] = url
    # Recorded usage is entirely reads. Blocks mutating tools at the server layer;
    # this guards against agent error, not against a hostile binary. Only the PAT
    # scope constrains the binary itself.
    # 3.x reads only the GITLAB_MCP_ name and refuses to start if GITLAB_READ_ONLY is set.
    env["GITLAB_MCP_READ_ONLY"] = os.environ.get("GITLAB_MCP_READ_ONLY", "true")
    env["AUTO_UPDATE"] = os.environ.get("AUTO_UPDATE", AUTO_UPDATE)

    # exec so the server owns stdio directly; nothing may sit between it and the client.
    os.execve(str(SERVER), [str(SERVER), *argv], env)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
