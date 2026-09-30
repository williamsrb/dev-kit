#!/usr/bin/env python3
"""Launch gitlab-mcp-server with credentials from AGENTS_HOME/.auth, not from mcp.json.

The server reads its token only from the environment; it has no token-file
option. This wrapper supplies the environment so no client config file has to
hold the secret.

Auth file (first match):
  $AGENTS_HOME/.auth/gitlab-access-token.yaml

Required keys: access_token. gitlab_url, or GITLAB_URL in the environment.
No hardcoded GitLab host.

Python 3.12, standard library only.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
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

# Auto-update is on by default: the binary replaces itself hourly from a
# single-maintainer GitHub repo. Pinning it means the reviewed binary is the one
# that keeps running; updates become a deliberate, verifiable step.
#
# The documented -auto-update flag is ignored in stdio mode (verified against
# 2.7.5: both "-auto-update false" and "-auto-update=false" still log mode=true).
# Only this environment variable actually disables the updater.
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


def load_auth(path: Path) -> dict[str, str]:
    """Parse the flat `key: "value"` auth file. Avoids a PyYAML dependency."""
    if not path.is_file():
        sys.exit(f"gitlab-mcp: missing credential file {path}")
    if path.stat().st_mode & 0o077:
        print(f"gitlab-mcp: {path} is group/world readable; chmod 600 it", file=sys.stderr)

    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def warn_on_expiry(expires_at: str) -> None:
    """A silently expired PAT looks like a broken server; say so on stderr instead."""
    try:
        expiry = date.fromisoformat(expires_at)
    except ValueError:
        return
    remaining = (expiry - datetime.now(timezone.utc).date()).days
    if remaining < 0:
        print(f"gitlab-mcp: token EXPIRED on {expires_at}; calls will fail", file=sys.stderr)
    elif remaining <= 30:
        print(f"gitlab-mcp: token expires in {remaining} day(s) ({expires_at})", file=sys.stderr)


def main(argv: list[str]) -> int:
    auth_file = resolve_auth_file()
    auth = load_auth(auth_file)
    token = auth.get("access_token", "")
    if not token:
        sys.exit(f"gitlab-mcp: no access_token in {auth_file}")
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
    env["GITLAB_READ_ONLY"] = os.environ.get("GITLAB_READ_ONLY", "true")
    env["AUTO_UPDATE"] = os.environ.get("AUTO_UPDATE", AUTO_UPDATE)

    # exec so the server owns stdio directly; nothing may sit between it and the client.
    os.execve(str(SERVER), [str(SERVER), *argv], env)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
