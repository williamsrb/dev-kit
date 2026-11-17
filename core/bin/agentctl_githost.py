"""Git host adapter for the parallel-issue sync (plan factory-sync).

One interface, one implementation per host flavor selected by `.agentctl [git_host] kind`: GitLab over its
REST API, a GitHub stub that fails clearly, and an in-memory fake for tests. The GitLab token is the entry
named by `[git_host.gitlab] token_name` in the `tokens:` list file that `bin/gitlab-mcp.py` also reads; this
module reuses that parser and refuses an expired token or one without the `api` scope.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import agentctl_config


class HostError(Exception):
    """The git host cannot be reached, or is not allowed to be written."""


@dataclass
class ReviewRequest:
    id: int
    title: str
    description: str
    source_branch: str
    target_branch: str
    state: str
    labels: list[str] = field(default_factory=list)
    web_url: str = ""


class Adapter(ABC):
    @abstractmethod
    def list_review_requests(self, *, target: str | None = None, source: str | None = None,
                             state: str = "opened") -> list[ReviewRequest]: ...

    @abstractmethod
    def changed_files(self, request_id: int) -> list[str]: ...

    @abstractmethod
    def create(self, source: str, target: str, title: str, description: str, labels: list[str]) -> ReviewRequest: ...

    @abstractmethod
    def comment(self, request_id: int, body: str) -> int: ...

    @abstractmethod
    def close(self, request_id: int) -> None: ...

    @abstractmethod
    def deployments(self, environment: str) -> list[dict[str, Any]]:
        """Latest deployments of `environment`, newest first: dicts with `id`, `sha`, `status`."""


# --------------------------------------------------------------------------- token and project


def _gitlab_mcp() -> Any:
    path = Path(__file__).resolve().parent / "gitlab-mcp.py"
    spec = importlib.util.spec_from_file_location("gitlab_mcp_tokens", path)
    if spec is None or spec.loader is None:
        raise HostError(f"cannot load the token parser {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_token(host_cfg: dict[str, Any], auth_dir: Path, *, today: date | None = None) -> dict[str, str]:
    """The token entry named by `token_name` from the first existing file of `auth_files`; must be `api` and unexpired."""
    names = host_cfg.get("auth_files") or []
    wanted = host_cfg.get("token_name")
    if not names or not wanted:
        raise HostError("no token configured for this git host (.agentctl [git_host.<kind>] auth_files, token_name)")
    path = next((auth_dir / n for n in names if (auth_dir / n).is_file()), None)
    if path is None:
        raise HostError("no credential file found: " + ", ".join(str(auth_dir / n) for n in names))
    try:
        entries = _gitlab_mcp().load_tokens(path)
    except SystemExit as exc:
        raise HostError(str(exc)) from exc
    entry = next((e for e in entries if e.get("key_name") == wanted), None)
    if entry is None or not entry.get("key_value"):
        raise HostError(f"no token named {wanted!r} in {path}")
    if entry.get("key_scope") and entry["key_scope"] != "api":
        raise HostError(f"token {wanted!r} has scope {entry['key_scope']!r}; the sync needs 'api'")
    try:
        expires = date.fromisoformat(entry.get("expires_at", ""))
    except ValueError:
        expires = None
    if expires and expires < (today or datetime.now(UTC).date()):
        raise HostError(f"token {wanted!r} expired on {entry['expires_at']}")
    return entry


def remote_project(url: str) -> tuple[str, str]:
    """(host, `group/repo`) of a git remote URL (ssh or https)."""
    match = re.match(r"^(?:[\w.-]+@)?([\w.-]+):(?!//)(.+?)(?:\.git)?/?$", url) \
        or re.match(r"^\w+://(?:[^@/]+@)?([\w.-]+)(?::\d+)?/(.+?)(?:\.git)?/?$", url)
    if not match:
        raise HostError(f"cannot read a project path from remote {url!r}")
    return match.group(1), match.group(2)


def project_from_remote(url: str, base_url: str) -> str:
    """`group/repo` of a git remote URL (ssh or https), checked against the host the token belongs to."""
    host = urllib.parse.urlparse(base_url).hostname or ""
    remote_host, project = remote_project(url)
    if remote_host != host:
        raise HostError(f"remote host {remote_host!r} is not the token's host {host!r}")
    return project


# --------------------------------------------------------------------------- GitLab


class GitLabAdapter(Adapter):
    def __init__(self, base_url: str, token: str, project: str, *, api_path: str = "/api/v4",
                 opener: Any = None) -> None:
        self.api = base_url.rstrip("/") + api_path
        self.token = token
        self.project = urllib.parse.quote(project, safe="")
        self.opener = opener or urllib.request.urlopen

    def _call(self, method: str, path: str, data: dict[str, Any] | None = None) -> Any:
        request = urllib.request.Request(
            f"{self.api}/projects/{self.project}{path}", method=method,
            headers={"PRIVATE-TOKEN": self.token, "Content-Type": "application/json"},
            data=None if data is None else json.dumps(data).encode())
        try:
            with self.opener(request, timeout=30) as response:
                body = response.read().decode()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            raise HostError(f"{method} {path} -> {exc.code} {exc.read().decode()[:200]}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise HostError(f"{method} {path} failed: {exc}") from exc

    @staticmethod
    def _request(raw: dict[str, Any]) -> ReviewRequest:
        return ReviewRequest(id=raw["iid"], title=raw.get("title", ""), description=raw.get("description") or "",
                             source_branch=raw["source_branch"], target_branch=raw["target_branch"],
                             state=raw.get("state", ""), labels=list(raw.get("labels") or []),
                             web_url=raw.get("web_url", ""))

    def list_review_requests(self, *, target: str | None = None, source: str | None = None,
                             state: str = "opened") -> list[ReviewRequest]:
        query = {"state": state, "per_page": "100"}
        if target:
            query["target_branch"] = target
        if source:
            query["source_branch"] = source
        return [self._request(r) for r in self._call("GET", "/merge_requests?" + urllib.parse.urlencode(query)) or []]

    def changed_files(self, request_id: int) -> list[str]:
        changes = self._call("GET", f"/merge_requests/{request_id}/changes") or {}
        return [c["new_path"] for c in changes.get("changes", [])]

    def create(self, source: str, target: str, title: str, description: str, labels: list[str]) -> ReviewRequest:
        return self._request(self._call("POST", "/merge_requests", {
            "source_branch": source, "target_branch": target, "title": title, "description": description,
            "labels": ",".join(labels), "remove_source_branch": False}))

    def comment(self, request_id: int, body: str) -> int:
        return int(self._call("POST", f"/merge_requests/{request_id}/notes", {"body": body})["id"])

    def close(self, request_id: int) -> None:
        self._call("PUT", f"/merge_requests/{request_id}", {"state_event": "close"})

    def deployments(self, environment: str) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({"environment": environment, "order_by": "id", "sort": "desc", "per_page": "20"})
        return [{"id": d["id"], "sha": d.get("sha", ""), "status": d.get("status", "")}
                for d in self._call("GET", "/deployments?" + query) or []]


class GitHubAdapter(Adapter):
    """No GitHub sync yet: every call fails with a clear message so a flipped config never half-works."""

    def _unsupported(self, *_: Any, **__: Any) -> Any:
        raise HostError("the GitHub adapter is not implemented; the sync supports GitLab only")

    list_review_requests = changed_files = create = comment = close = deployments = _unsupported


# --------------------------------------------------------------------------- fake for tests


class FakeAdapter(Adapter):
    """In-memory host. `fail` makes every call raise, to prove unverified/host_unavailable paths."""

    def __init__(self, requests: list[ReviewRequest] | None = None, files: dict[int, list[str]] | None = None) -> None:
        self.requests = list(requests or [])
        self.files = dict(files or {})
        self.comments: list[tuple[int, str]] = []
        self.fail = False

    def _check(self) -> None:
        if self.fail:
            raise HostError("host unavailable")

    def list_review_requests(self, *, target: str | None = None, source: str | None = None,
                             state: str = "opened") -> list[ReviewRequest]:
        self._check()
        return [r for r in self.requests if (state == "all" or r.state == state)
                and (target is None or r.target_branch == target) and (source is None or r.source_branch == source)]

    def changed_files(self, request_id: int) -> list[str]:
        self._check()
        return list(self.files.get(request_id, []))

    def create(self, source: str, target: str, title: str, description: str, labels: list[str]) -> ReviewRequest:
        self._check()
        request = ReviewRequest(len(self.requests) + 1, title, description, source, target, "opened", list(labels))
        self.requests.append(request)
        return request

    def comment(self, request_id: int, body: str) -> int:
        self._check()
        self.comments.append((request_id, body))
        return len(self.comments)

    def close(self, request_id: int) -> None:
        self._check()
        next(r for r in self.requests if r.id == request_id).state = "closed"

    def deployments(self, environment: str) -> list[dict[str, Any]]:
        self._check()
        return []


# --------------------------------------------------------------------------- factory


def adapter_for(cfg: dict[str, Any], repo: Path, auth_dir: Path, *, remote: str = "origin") -> Adapter:
    """The adapter for the active `[git_host]` flavor, bound to `repo`'s `remote` project."""
    host = agentctl_config.git_host(cfg)
    if host is None:
        raise HostError(".agentctl [git_host] kind is 'none'")
    if host["kind"] == "github":
        return GitHubAdapter()
    if host["kind"] != "gitlab":
        raise HostError(f"no sync adapter for git host {host['kind']!r}")
    token = load_token(host, auth_dir)
    url = subprocess.run(["git", "remote", "get-url", remote], cwd=repo, text=True, capture_output=True, check=False)
    if url.returncode != 0:
        raise HostError(f"repo {repo} has no remote named {remote!r}")
    base = os.environ.get("GITLAB_URL") or token["gitlab_url"]
    return GitLabAdapter(base, token["key_value"], project_from_remote(url.stdout.strip(), base),
                         api_path=host["api_path"])
