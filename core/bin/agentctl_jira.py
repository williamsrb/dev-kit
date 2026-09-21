"""Jira/Confluence REST client for agentctl.

Uses the site API token at ~/.agents/.auth/jira-api-token.yaml. Maps the
Atlassian MCP operations this harness actually uses onto Cloud REST v3 so
agents can batch deterministic calls without a model round-trip per request.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SITE = ""


def agents_home() -> Path:
    """Harness root: $AGENTS_HOME when a profile wrapper set it, else ~/.agents."""
    raw = os.environ.get("AGENTS_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".agents"


TOKEN_PATH = agents_home() / ".auth" / "jira-api-token.yaml"
PRD_ROOT = agents_home() / "prds"
RENDER_SCRIPT = (
    agents_home() / "skills" / "download-jira-task" / "scripts" / "render_issue.py"
)
DEFAULT_ISSUE_FIELDS = [
    "summary",
    "description",
    "status",
    "issuetype",
    "priority",
    "assignee",
    "reporter",
    "created",
    "updated",
    "project",
    "comment",
    "attachment",
]
RICH_TEXT_FIELDS = {"description", "environment", "comment"}
USER_FIELDS = {"assignee", "reporter"}
NAME_OBJECT_FIELDS = {"issuetype", "priority", "status"}
SYSTEM_FIELD_IDS = {
    "summary", "description", "environment", "duedate", "labels", "components",
    "fixversions", "versions", "issuetype", "project", "assignee", "reporter",
    "priority", "parent", "issuelinks", "attachment", "comment", "status",
    "resolution", "timetracking", "worklog",
}

CAPABILITIES = {
    "getJiraIssue": "agentctl jira get KEY",
    "getJiraIssue+attachments+PRD": "agentctl jira fetch KEY",
    "downloadJiraIssueAttachment": "agentctl jira fetch KEY (or jira attach --download ID)",
    "searchJiraIssuesUsingJql": "agentctl jira search 'JQL'",
    "addOrEditJiraIssueComment": "agentctl jira comment KEY --body TEXT [--comment-id ID]",
    "createJiraIssue": "agentctl jira create --project KEY --type TYPE --summary TEXT",
    "editJiraIssue": "agentctl jira edit KEY --fields JSON",
    "transitionJiraIssue": "agentctl jira transition KEY --to STATUS",
    "atlassianUserInfo": "agentctl jira myself",
    "getAccessibleAtlassianResources": "agentctl jira resources",
    "uploadAttachmentToJiraIssue": "agentctl jira attach KEY FILE",
    "jira-work-item-blocks-jira-work-item": "agentctl jira link FROM --type Blocks --to TO",
    "getConfluenceContent": "agentctl jira wiki-get ID",
    "searchConfluence": "agentctl jira wiki-search 'CQL'",
    "createConfluenceContent (page)": "agentctl jira wiki-create --space KEY --title TEXT",
    "updateConfluenceContent (page)": "agentctl jira wiki-update ID --title TEXT --body HTML",
    "executeRead/Write via REST": "agentctl jira request METHOD PATH [--body JSON]",
    "inline existing attachment in a body": "agentctl jira media-ids KEY",
}
UNSUPPORTED = [
    "Rovo semantic search (search tool)",
    "Teamwork Graph except Jira issue links",
    "MCP discover catalog (~227 named operations)",
    "Confluence whiteboard/database/embed SVG-CSV create",
    "inline MCP media collections (inlineFileId) for NEW uploads; existing attachments can be embedded via jira media-ids",
]


class JiraError(Exception):
    def __init__(self, status: int, message: str, payload: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload


class StripAuthOnHostChange(urllib.request.HTTPRedirectHandler):
    """Do not forward Basic auth to media CDNs after /attachment/content redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is None:
            return None
        old_host = urllib.parse.urlparse(req.full_url).netloc
        new_host = urllib.parse.urlparse(new.full_url).netloc
        if old_host != new_host:
            headers = dict(new.header_items())
            headers.pop("Authorization", None)
            new.headers = headers
            if hasattr(new, "unredirected_hdrs"):
                new.unredirected_hdrs.pop("Authorization", None)
        return new


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Surface the 303 from /attachment/content instead of following it.

    The Location header carries the media file UUID, which is the id an ADF
    media node needs. It is not the numeric attachment id, and no Jira REST
    field exposes it.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        return None


def load_yaml_map(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid credential line in {path}")
        key, _, value = line.partition(":")
        data[key.strip()] = _unquote(value.strip())
    return data


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_credentials(path: Path | None = None, site: str | None = None) -> dict[str, str]:
    token_path = (path or TOKEN_PATH).expanduser()
    if not token_path.is_file():
        raise FileNotFoundError(
            f"Jira API token file not found: {token_path}. "
            "Expected user and api_token keys."
        )
    raw = load_yaml_map(token_path)
    user = raw.get("user", "").strip()
    token = raw.get("api_token", "").strip()
    if not user or not token:
        raise ValueError(f"{token_path} must contain user and api_token")
    creds = {
        "path": str(token_path),
        "user": user,
        "api_token": token,
        "site": (site or raw.get("site") or raw.get("base_url") or DEFAULT_SITE).rstrip("/"),
        "token_name": raw.get("token_name", ""),
        "created_at": raw.get("created_at", ""),
        "expires_at": raw.get("expires_at", ""),
        "mode": oct(token_path.stat().st_mode & 0o777),
    }
    if not creds["site"]:
        raise ValueError(
            f"{token_path} has no site key; add site: https://<name>.atlassian.net or pass --site"
        )
    return creds


def public_auth(creds: dict[str, str]) -> dict[str, Any]:
    expires = creds.get("expires_at") or ""
    expired = False
    if expires:
        try:
            expired = date.fromisoformat(expires[:10]) < datetime.now(timezone.utc).date()
        except ValueError:
            expired = False
    return {
        "path": creds["path"],
        "user": creds["user"],
        "site": creds["site"],
        "token_name": creds.get("token_name") or None,
        "created_at": creds.get("created_at") or None,
        "expires_at": expires or None,
        "expired": expired,
        "world_readable": creds.get("mode") in {"0o644", "0o664", "0o666", "0o755"},
    }


def _error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        if payload.get("message"):
            return str(payload["message"])
        errors = payload.get("errorMessages")
        if isinstance(errors, list) and errors:
            return "; ".join(str(item) for item in errors)
        keyed = payload.get("errors")
        if isinstance(keyed, dict) and keyed:
            return "; ".join(f"{k}: {v}" for k, v in keyed.items())
    return "Jira request failed"


def _looks_like_adf(value: Any) -> bool:
    return isinstance(value, dict) and value.get("type") == "doc"


def inline_adf(text: str) -> list[dict[str, Any]]:
    """Convert a subset of Markdown inline markup to ADF text nodes."""
    nodes: list[dict[str, Any]] = []
    pattern = re.compile(
        r"(`[^`]+`)"
        r"|(\*\*[^*]+\*\*)"
        r"|(\*[^*]+\*)"
        r"|(\[[^\]]+\]\([^)]+\))"
        r"|(_[^_]+_)"
    )
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            chunk = text[pos:match.start()]
            if chunk:
                nodes.append({"type": "text", "text": chunk})
        token = match.group(0)
        if token.startswith("`"):
            nodes.append({"type": "text", "text": token[1:-1], "marks": [{"type": "code"}]})
        elif token.startswith("**"):
            nodes.append({"type": "text", "text": token[2:-2], "marks": [{"type": "strong"}]})
        elif token.startswith(("*", "_")):
            nodes.append({"type": "text", "text": token[1:-1], "marks": [{"type": "em"}]})
        else:
            label, _, href = token[1:-1].partition("](")
            nodes.append({
                "type": "text",
                "text": label,
                "marks": [{"type": "link", "attrs": {"href": href}}],
            })
        pos = match.end()
    if pos < len(text):
        nodes.append({"type": "text", "text": text[pos:]})
    return nodes or []


CHECKBOX_RE = re.compile(r"^(\*|-)\s+\[([ xX])\]\s*(.*)$")


def _adf_local_id() -> str:
    return str(uuid.uuid4())


def markdown_to_adf(text: str) -> dict[str, Any]:
    if _looks_like_adf(text):
        return text  # type: ignore[return-value]
    if isinstance(text, str):
        stripped = text.strip()
        if stripped.startswith("{") and '"type"' in stripped:
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if _looks_like_adf(parsed):
                return parsed
    body = str(text).replace("\r\n", "\n")
    lines = body.split("\n")
    blocks: list[dict[str, Any]] = []
    index = 0

    def emit_list(start: int) -> int:
        ordered = bool(re.match(r"^\d+\.\s+", lines[start]))
        items: list[dict[str, Any]] = []
        pos = start
        marker = re.compile(r"^\d+\.\s+" if ordered else r"^(\*|-)\s+")
        while pos < len(lines) and marker.match(lines[pos]):
            if not ordered and CHECKBOX_RE.match(lines[pos]):
                break
            item_text = marker.sub("", lines[pos], count=1)
            items.append({
                "type": "listItem",
                "content": [{"type": "paragraph", "content": inline_adf(item_text)}],
            })
            pos += 1
        blocks.append({
            "type": "orderedList" if ordered else "bulletList",
            "content": items,
        })
        return pos

    def emit_task_list(start: int) -> int:
        items: list[dict[str, Any]] = []
        pos = start
        while pos < len(lines):
            match = CHECKBOX_RE.match(lines[pos])
            if not match:
                break
            state = "DONE" if match.group(2).lower() == "x" else "TODO"
            items.append({
                "type": "taskItem",
                "attrs": {"localId": _adf_local_id(), "state": state},
                "content": inline_adf(match.group(3)),
            })
            pos += 1
        blocks.append({
            "type": "taskList",
            "attrs": {"localId": _adf_local_id()},
            "content": items,
        })
        return pos

    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            language = line[3:].strip()
            collected: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                collected.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            block: dict[str, Any] = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": "\n".join(collected)}],
            }
            if language:
                block["attrs"] = {"language": language}
            blocks.append(block)
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            blocks.append({
                "type": "heading",
                "attrs": {"level": len(heading.group(1))},
                "content": inline_adf(heading.group(2)),
            })
            index += 1
            continue
        if CHECKBOX_RE.match(line):
            index = emit_task_list(index)
            continue
        if re.match(r"^(\*|-|\d+\.)\s+", line):
            index = emit_list(index)
            continue
        if line.strip() == "---":
            blocks.append({"type": "rule"})
            index += 1
            continue
        if not line.strip():
            index += 1
            continue
        para = [line]
        index += 1
        while index < len(lines) and lines[index].strip():
            if lines[index].startswith("```") or re.match(r"^(#{1,6})\s+", lines[index]):
                break
            if re.match(r"^(\*|-|\d+\.)\s+", lines[index]):
                break
            para.append(lines[index])
            index += 1
        blocks.append({"type": "paragraph", "content": inline_adf(" ".join(para))})
    if not blocks:
        blocks = [{"type": "paragraph", "content": []}]
    return {"type": "doc", "version": 1, "content": blocks}


def html_to_adf(text: str) -> dict[str, Any]:
    render = load_render_issue()
    return markdown_to_adf(render.html_to_md(text))


def adf_to_adf(text: str) -> dict[str, Any]:
    """Parse a raw ADF document, failing loudly rather than degrading to markdown.

    markdown_to_adf also passes ADF through, but silently renders the raw JSON as
    text when it does not parse. Media, mentions and tables have no markdown
    representation, so that fallback publishes a visibly broken comment instead of
    reporting the problem.
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--content-format adf needs a JSON document: {exc}") from exc
    if not _looks_like_adf(parsed):
        got = parsed.get("type") if isinstance(parsed, dict) else type(parsed).__name__
        raise ValueError(
            f'--content-format adf needs a top-level {{"type": "doc", ...}} node, got {got!r}'
        )
    return parsed


def body_to_adf(value: Any, content_format: str = "markdown") -> dict[str, Any]:
    if _looks_like_adf(value):
        return value
    text = "" if value is None else str(value)
    if content_format == "adf":
        return adf_to_adf(text)
    if content_format == "html":
        return html_to_adf(text)
    return markdown_to_adf(text)


def load_render_issue() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("render_issue", RENDER_SCRIPT)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"render_issue.py not found: {RENDER_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_automated_comments(
    issue: dict[str, Any],
    *,
    include_bots: bool = False,
    strict_bots: bool = False,
) -> int:
    """Drop GitLab/Jira integration spam. Same rule as render_issue.py / SKILL.md."""
    render = load_render_issue()
    fields = issue.get("fields") or {}
    comment = fields.get("comment")
    if isinstance(comment, list):
        comment = {"comments": comment, "total": len(comment)}
        fields["comment"] = comment
        issue["fields"] = fields
    if not isinstance(comment, dict):
        issue["skipped_bot_comments"] = 0
        return 0
    kept: list[dict[str, Any]] = []
    skipped = 0
    for item in comment.get("comments") or []:
        if not isinstance(item, dict):
            continue
        author = render.name(item.get("author"))
        if render.keep_comment(author, include_bots, strict_bots):
            kept.append(item)
        else:
            skipped += 1
    comment["comments"] = kept
    comment["total"] = len(kept)
    comment["skipped"] = skipped
    fields["comment"] = comment
    issue["fields"] = fields
    issue["skipped_bot_comments"] = skipped
    return skipped


def issue_bodies_as_markdown(issue: dict[str, Any]) -> dict[str, Any]:
    render = load_render_issue()
    cloned = json.loads(json.dumps(issue))
    fields = cloned.get("fields") or {}
    fields["description"] = render.body_to_md(fields.get("description"), None)
    comments = fields.get("comment")
    if isinstance(comments, dict):
        for comment in comments.get("comments") or []:
            if isinstance(comment, dict):
                comment["body"] = render.body_to_md(comment.get("body"), None)
    cloned["fields"] = fields
    cloned["appliedContentFormat"] = "markdown"
    return cloned


def pick_fields(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_ISSUE_FIELDS)
    return [item.strip() for item in raw.split(",") if item.strip()]


class JiraClient:
    def __init__(self, creds: dict[str, str], timeout: float = 60.0) -> None:
        self.site = creds["site"].rstrip("/")
        self.timeout = timeout
        token = f"{creds['user']}:{creds['api_token']}".encode()
        self._auth = "Basic " + base64.b64encode(token).decode("ascii")
        self._opener = urllib.request.build_opener(StripAuthOnHostChange())
        self._field_map: dict[str, str] | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: Any = None,
        content_type: str | None = None,
        extra_headers: dict[str, str] | None = None,
        accept: str = "application/json",
    ) -> Any:
        url = path if path.startswith(("http://", "https://")) else self.site + path
        if query:
            encoded = urllib.parse.urlencode(
                {key: value for key, value in query.items() if value is not None},
                doseq=True,
            )
            url = url + ("&" if "?" in url else "?") + encoded
        data: bytes | None = None
        headers = {
            "Authorization": self._auth,
            "Accept": accept,
            "User-Agent": "agentctl-jira",
        }
        if extra_headers:
            headers.update(extra_headers)
        if body is not None:
            if isinstance(body, (bytes, bytearray)):
                data = bytes(body)
                headers["Content-Type"] = content_type or "application/octet-stream"
            else:
                data = json.dumps(body).encode("utf-8")
                headers["Content-Type"] = content_type or "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
                if not raw:
                    return None
                ctype = response.headers.get("Content-Type", "")
                if accept != "application/json" and "json" not in ctype:
                    return raw
                if "json" in ctype or raw[:1] in (b"{", b"["):
                    return json.loads(raw.decode("utf-8"))
                return raw
        except urllib.error.HTTPError as exc:
            err_raw = exc.read()
            payload: Any
            try:
                payload = json.loads(err_raw.decode("utf-8"))
            except Exception:
                payload = {"raw": err_raw.decode("utf-8", "replace")[:2000]}
            raise JiraError(exc.code, _error_message(payload), payload) from None

    def field_id(self, name: str) -> str:
        key = name.strip()
        if key.lower().startswith("customfield_") or key.lower() in SYSTEM_FIELD_IDS:
            return key
        if self._field_map is None:
            catalog = self.request("GET", "/rest/api/3/field")
            mapping: dict[str, str] = {}
            if isinstance(catalog, list):
                for item in catalog:
                    if not isinstance(item, dict):
                        continue
                    field_id = str(item.get("id") or "")
                    field_name = str(item.get("name") or "").strip().lower()
                    if field_id and field_name and field_name not in mapping:
                        mapping[field_name] = field_id
            self._field_map = mapping
        return self._field_map.get(key.lower(), key)

    def resolve_user(self, value: Any) -> Any:
        if value is None or isinstance(value, dict):
            return value
        text = str(value).strip()
        if not text:
            return None
        if re.fullmatch(r"[0-9a-f:-]{20,}", text) or text.startswith("qm:"):
            return {"accountId": text}
        found = self.request("GET", "/rest/api/3/user/search", query={"query": text})
        if isinstance(found, list) and found:
            account = found[0].get("accountId")
            if account:
                return {"accountId": account}
        return {"accountId": text}

    def normalize_fields(self, fields: dict[str, Any], *, content_format: str = "markdown") -> dict[str, Any]:
        out: dict[str, Any] = {}
        for raw_key, value in fields.items():
            key = self.field_id(raw_key)
            lowered = key.lower()
            if value is None:
                out[key] = None
                continue
            if lowered in RICH_TEXT_FIELDS and isinstance(value, str):
                out[key] = body_to_adf(value, content_format)
            elif lowered in USER_FIELDS:
                out[key] = self.resolve_user(value)
            elif lowered in NAME_OBJECT_FIELDS and isinstance(value, str):
                out[key] = {"name": value}
            elif lowered == "project" and isinstance(value, str):
                out[key] = {"key": value}
            elif lowered == "parent" and isinstance(value, str):
                out[key] = {"key": value}
            elif lowered == "labels" and isinstance(value, str):
                out[key] = [item.strip() for item in value.split(",") if item.strip()]
            else:
                out[key] = value
        return out

    def myself(self) -> dict[str, Any]:
        return self.request("GET", "/rest/api/3/myself")

    def server_info(self) -> dict[str, Any]:
        return self.request("GET", "/rest/api/3/serverInfo")

    def get_issue(
        self,
        key: str,
        fields: list[str] | None = None,
        *,
        include_bots: bool = False,
        strict_bots: bool = False,
    ) -> dict[str, Any]:
        issue = self.request(
            "GET",
            f"/rest/api/3/issue/{urllib.parse.quote(key)}",
            query={"fields": ",".join(fields or DEFAULT_ISSUE_FIELDS)},
        )
        if not isinstance(issue, dict):
            raise JiraError(500, "unexpected issue payload")
        self._fill_comments(issue)
        strip_automated_comments(issue, include_bots=include_bots, strict_bots=strict_bots)
        return issue

    def _fill_comments(self, issue: dict[str, Any]) -> None:
        fields = issue.get("fields") or {}
        comment = fields.get("comment") or {}
        if not isinstance(comment, dict):
            return
        total = int(comment.get("total") or 0)
        kept = list(comment.get("comments") or [])
        start = len(kept)
        while start < total:
            page = self.request(
                "GET",
                f"/rest/api/3/issue/{urllib.parse.quote(issue['key'])}/comment",
                query={"startAt": start, "maxResults": 100, "orderBy": "created"},
            )
            batch = page.get("comments") if isinstance(page, dict) else None
            if not batch:
                break
            kept.extend(batch)
            start = len(kept)
            total = int(page.get("total") or total)
        comment["comments"] = kept
        comment["total"] = len(kept)
        fields["comment"] = comment
        issue["fields"] = fields

    def search(
        self,
        jql: str,
        *,
        fields: list[str] | None = None,
        max_results: int = 50,
        next_page_token: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "fields": fields or ["summary", "status", "issuetype", "updated", "assignee", "attachment"],
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token
        try:
            return self.request("POST", "/rest/api/3/search/jql", body=payload)
        except JiraError as exc:
            if exc.status != 410 and exc.status != 404:
                raise
            legacy = self.request(
                "GET",
                "/rest/api/3/search",
                query={
                    "jql": jql,
                    "maxResults": max_results,
                    "fields": ",".join(payload["fields"]),
                    "startAt": next_page_token or 0,
                },
            )
            if isinstance(legacy, dict) and "nextPageToken" not in legacy:
                start = int(legacy.get("startAt") or 0)
                size = int(legacy.get("maxResults") or max_results)
                total = int(legacy.get("total") or 0)
                legacy["isLast"] = start + size >= total
            return legacy

    def add_or_edit_comment(
        self,
        key: str,
        body: str,
        *,
        comment_id: str | None = None,
        content_format: str = "markdown",
        visibility: dict[str, str] | None = None,
        jsm_internal: bool | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"body": body_to_adf(body, content_format)}
        if visibility:
            payload["visibility"] = visibility
        if jsm_internal is True:
            payload["properties"] = [
                {"key": "sd.public.comment", "value": {"internal": True}},
            ]
        quoted = urllib.parse.quote(key)
        if comment_id:
            return self.request(
                "PUT",
                f"/rest/api/3/issue/{quoted}/comment/{urllib.parse.quote(comment_id)}",
                body=payload,
            )
        return self.request("POST", f"/rest/api/3/issue/{quoted}/comment", body=payload)

    def attachment_media_id(self, attachment_id: str) -> str | None:
        """Media file UUID for an attachment already on an issue, or None."""
        url = f"{self.site}/rest/api/3/attachment/content/{urllib.parse.quote(str(attachment_id))}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": self._auth,
                "Accept": "*/*",
                "User-Agent": "agentctl-jira",
            },
            method="GET",
        )
        opener = urllib.request.build_opener(NoRedirect())
        try:
            opener.open(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            if exc.code not in (301, 302, 303, 307, 308):
                raise JiraError(exc.code, f"attachment {attachment_id}: {exc.reason}") from exc
            match = re.search(r"/file/([0-9a-fA-F-]{36})", exc.headers.get("Location", "") or "")
            return match.group(1) if match else None
        return None

    def create_issue(self, fields: dict[str, Any], *, content_format: str = "markdown") -> dict[str, Any]:
        return self.request(
            "POST",
            "/rest/api/3/issue",
            body={"fields": self.normalize_fields(fields, content_format=content_format)},
        )

    def edit_issue(self, key: str, fields: dict[str, Any], *, content_format: str = "markdown") -> Any:
        return self.request(
            "PUT",
            f"/rest/api/3/issue/{urllib.parse.quote(key)}",
            body={"fields": self.normalize_fields(fields, content_format=content_format)},
        )

    def transitions(self, key: str) -> list[dict[str, Any]]:
        payload = self.request("GET", f"/rest/api/3/issue/{urllib.parse.quote(key)}/transitions")
        items = payload.get("transitions") if isinstance(payload, dict) else None
        return items if isinstance(items, list) else []

    def transition(self, key: str, to_status: str, fields: dict[str, Any] | None = None) -> Any:
        wanted = to_status.strip().lower()
        matches = [
            item for item in self.transitions(key)
            if str(item.get("name") or "").lower() == wanted
            or str((item.get("to") or {}).get("name") or "").lower() == wanted
            or str(item.get("id") or "") == to_status.strip()
        ]
        if not matches:
            names = [item.get("name") for item in self.transitions(key)]
            raise JiraError(400, f"no transition matching {to_status!r}; available: {names}")
        body: dict[str, Any] = {"transition": {"id": matches[0]["id"]}}
        if fields:
            body["fields"] = self.normalize_fields(fields)
        return self.request("POST", f"/rest/api/3/issue/{urllib.parse.quote(key)}/transitions", body=body)

    def download_attachment(self, attachment_id: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = self.request(
            "GET",
            f"/rest/api/3/attachment/content/{urllib.parse.quote(attachment_id)}",
            accept="*/*",
        )
        if not isinstance(raw, (bytes, bytearray)):
            raise JiraError(500, f"attachment {attachment_id} did not return bytes")
        dest.write_bytes(bytes(raw))
        return dest

    def upload_attachment(self, key: str, path: Path) -> Any:
        filename = path.name
        payload = path.read_bytes()
        boundary = "----agentctl" + secrets.token_hex(8)
        blob = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8") + payload + f"\r\n--{boundary}--\r\n".encode("ascii")
        return self.request(
            "POST",
            f"/rest/api/3/issue/{urllib.parse.quote(key)}/attachments",
            body=blob,
            content_type=f"multipart/form-data; boundary={boundary}",
            extra_headers={"X-Atlassian-Token": "no-check"},
        )

    def link_issues(self, source: str, link_type: str, target: str) -> Any:
        return self.request(
            "POST",
            "/rest/api/3/issueLink",
            body={
                "type": {"name": link_type},
                "outwardIssue": {"key": source},
                "inwardIssue": {"key": target},
            },
        )

    def wiki_get(self, content_id: str) -> Any:
        return self.request(
            "GET",
            f"/wiki/rest/api/content/{urllib.parse.quote(content_id)}",
            query={"expand": "body.storage,body.view,version,space,_links"},
        )

    def wiki_search(self, cql: str, limit: int = 25) -> Any:
        return self.request(
            "GET",
            "/wiki/rest/api/content/search",
            query={"cql": cql, "limit": limit, "expand": "space,version"},
        )

    def wiki_create(
        self,
        *,
        space: str,
        title: str,
        body: str,
        content_type: str = "page",
        parent_id: str | None = None,
        representation: str = "storage",
    ) -> Any:
        payload: dict[str, Any] = {
            "type": content_type,
            "title": title,
            "space": {"key": space},
            "body": {representation: {"value": body, "representation": representation}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        return self.request("POST", "/wiki/rest/api/content", body=payload)

    def wiki_update(
        self,
        content_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
        representation: str = "storage",
    ) -> Any:
        current = self.wiki_get(content_id)
        version = int((current.get("version") or {}).get("number") or 1) + 1
        payload: dict[str, Any] = {
            "type": current.get("type") or "page",
            "title": title or current.get("title"),
            "version": {"number": version},
        }
        if body is not None:
            payload["body"] = {representation: {"value": body, "representation": representation}}
        return self.request(
            "PUT",
            f"/wiki/rest/api/content/{urllib.parse.quote(content_id)}",
            body=payload,
        )


def client_from_args(args: argparse.Namespace) -> JiraClient:
    creds = load_credentials(getattr(args, "token_file", None), getattr(args, "site", None))
    return JiraClient(creds, timeout=float(getattr(args, "timeout", 60.0)))


def emit_error(exc: Exception) -> int:
    payload: dict[str, Any] = {"status": "error", "error": str(exc), "type": type(exc).__name__}
    if isinstance(exc, JiraError):
        payload["http_status"] = exc.status
        if isinstance(exc.payload, dict):
            payload["jira"] = {
                key: exc.payload.get(key)
                for key in ("errorMessages", "errors", "message")
                if exc.payload.get(key) is not None
            }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 1


def parse_json_arg(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("--fields must be a JSON object")
    return value


def parse_visibility(raw: str | None) -> dict[str, str] | None:
    if not raw:
        return None
    kind, _, value = raw.partition(":")
    kind = kind.strip().lower()
    if kind not in {"group", "role"} or not value.strip():
        raise ValueError("--visibility must be group:NAME or role:NAME")
    return {"type": kind, "value": value.strip()}


def cmd_jira_capabilities(args: argparse.Namespace) -> int:
    present = False
    auth: dict[str, Any] | None = None
    try:
        creds = load_credentials(args.token_file, args.site)
        auth = public_auth(creds)
        present = True
    except (OSError, ValueError) as exc:
        auth = {"error": str(exc), "path": str((args.token_file or TOKEN_PATH).expanduser())}
    print(json.dumps({
        "status": "ok",
        "auth": auth,
        "token_present": present,
        "mcp_equivalents": CAPABILITIES,
        "unsupported": UNSUPPORTED,
    }, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if present else 2


def cmd_jira_myself(args: argparse.Namespace) -> int:
    try:
        creds = load_credentials(args.token_file, args.site)
        me = JiraClient(creds, timeout=args.timeout).myself()
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)
    print(json.dumps({
        "status": "ok",
        "auth": public_auth(creds),
        "accountId": me.get("accountId"),
        "displayName": me.get("displayName"),
        "emailAddress": me.get("emailAddress"),
        "timeZone": me.get("timeZone"),
        "mcp": "atlassianUserInfo",
    }, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_jira_resources(args: argparse.Namespace) -> int:
    try:
        creds = load_credentials(args.token_file, args.site)
        client = JiraClient(creds, timeout=args.timeout)
        info = client.server_info()
        me = client.myself()
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)
    print(json.dumps({
        "status": "ok",
        "mcp": "getAccessibleAtlassianResources",
        "resources": [{
            "url": info.get("baseUrl") or creds["site"],
            "name": info.get("serverTitle") or urllib.parse.urlparse(creds["site"]).hostname,
            "site": creds["site"],
        }],
        "user": {"accountId": me.get("accountId"), "displayName": me.get("displayName")},
        "version": info.get("version"),
        "deploymentType": info.get("deploymentType"),
    }, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_jira_get(args: argparse.Namespace) -> int:
    try:
        client = client_from_args(args)
        issue = client.get_issue(
            args.issue,
            pick_fields(args.fields),
            include_bots=getattr(args, "include_bots", False),
            strict_bots=getattr(args, "strict_bots", False),
        )
        if args.format == "markdown":
            issue = issue_bodies_as_markdown(issue)
        if args.output:
            dest = args.output.expanduser()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(issue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            fields = issue.get("fields") or {}
            attachments = fields.get("attachment") or []
            comments = (fields.get("comment") or {}).get("comments") or []
            print(json.dumps({
                "status": "ok",
                "mcp": "getJiraIssue",
                "key": issue.get("key"),
                "summary": fields.get("summary"),
                "output": str(dest),
                "comments": len(comments) if isinstance(comments, list) else 0,
                "skipped_bot_comments": issue.get("skipped_bot_comments", 0),
                "attachments": len(attachments) if isinstance(attachments, list) else 0,
                "format": args.format,
            }, indent=2, ensure_ascii=False, sort_keys=True))
            return 0
        print(json.dumps(issue, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def cmd_jira_fetch(args: argparse.Namespace) -> int:
    try:
        client = client_from_args(args)
        render = load_render_issue()
        issue = client.get_issue(
            args.issue,
            pick_fields(args.fields),
            include_bots=getattr(args, "include_bots", False),
            strict_bots=getattr(args, "strict_bots", False),
        )
        prd_root = args.prd_root.expanduser()
        prd_root.mkdir(parents=True, exist_ok=True)
        old_root = render.PRD_ROOT
        render.PRD_ROOT = prd_root
        try:
            key, markdown, metadata = render.render(
                issue,
                getattr(args, "include_bots", False),
                getattr(args, "strict_bots", False),
            )
            files = render.list_attachments(issue.get("fields") or {}, key, prd_root)
        finally:
            render.PRD_ROOT = old_root
        downloaded: list[str] = []
        failed: list[dict[str, str]] = []
        if not args.no_attachments:
            for item in files:
                dest = Path(item["outputPath"])
                try:
                    client.download_attachment(str(item["id"]), dest)
                    downloaded.append(str(item["id"]))
                except JiraError as exc:
                    failed.append({"id": str(item["id"]), "error": str(exc)})
        prd = prd_root / f"{key}.md"
        prd.write_text(markdown, encoding="utf-8")
        if args.save_raw:
            raw_path = prd_root / f"{key}.json"
            raw_path.write_text(json.dumps(issue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            raw_path = None
        print(json.dumps({
            "status": "ok" if not failed else "partial",
            "mcp": "getJiraIssue+downloadJiraIssueAttachment",
            "key": key,
            "prd": str(prd),
            "raw": str(raw_path) if raw_path else None,
            "attachments_dir": str(render.attachments_dir(key, prd_root)),
            "comments": metadata.get("comments"),
            "attachments": metadata.get("attachments"),
            "downloaded": downloaded,
            "download_failed": failed,
            "skipped_bot_comments": issue.get("skipped_bot_comments", metadata.get("skipped_bot_comments")),
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if not failed else 2
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def cmd_jira_search(args: argparse.Namespace) -> int:
    try:
        client = client_from_args(args)
        payload = client.search(
            args.jql,
            fields=pick_fields(args.fields) if args.fields else None,
            max_results=args.max_results,
            next_page_token=args.next_page_token,
        )
        issues = payload.get("issues") if isinstance(payload, dict) else None
        compact = []
        for issue in issues or []:
            fields = issue.get("fields") or {}
            item = {
                "key": issue.get("key"),
                "id": issue.get("id"),
                "summary": fields.get("summary"),
                "status": (fields.get("status") or {}).get("name")
                if isinstance(fields.get("status"), dict) else fields.get("status"),
                "issuetype": (fields.get("issuetype") or {}).get("name")
                if isinstance(fields.get("issuetype"), dict) else fields.get("issuetype"),
                "updated": fields.get("updated"),
                "assignee": (fields.get("assignee") or {}).get("displayName")
                if isinstance(fields.get("assignee"), dict) else fields.get("assignee"),
                "attachment_count": len(fields.get("attachment") or [])
                if isinstance(fields.get("attachment"), list) else 0,
            }
            if args.full:
                strip_automated_comments(
                    issue,
                    include_bots=getattr(args, "include_bots", False),
                    strict_bots=getattr(args, "strict_bots", False),
                )
                item["issue"] = issue_bodies_as_markdown(issue) if args.format == "markdown" else issue
            compact.append(item)
        print(json.dumps({
            "status": "ok",
            "mcp": "searchJiraIssuesUsingJql",
            "jql": args.jql,
            "count": len(compact),
            "isLast": payload.get("isLast"),
            "nextPageToken": payload.get("nextPageToken"),
            "total": payload.get("total"),
            "issues": compact,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def cmd_jira_comment(args: argparse.Namespace) -> int:
    try:
        body = args.body
        if args.body_file:
            body = args.body_file.expanduser().read_text(encoding="utf-8")
        if body is None:
            raise ValueError("pass --body or --body-file")
        client = client_from_args(args)
        result = client.add_or_edit_comment(
            args.issue,
            body,
            comment_id=args.comment_id,
            content_format=args.content_format,
            visibility=parse_visibility(args.visibility),
            jsm_internal=True if args.internal else None,
        )
        print(json.dumps({
            "status": "ok",
            "mcp": "addOrEditJiraIssueComment",
            "id": result.get("id") if isinstance(result, dict) else None,
            "created": result.get("created") if isinstance(result, dict) else None,
            "updated": result.get("updated") if isinstance(result, dict) else None,
            "edited": bool(args.comment_id),
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError, json.JSONDecodeError) as exc:
        return emit_error(exc)


def cmd_jira_create(args: argparse.Namespace) -> int:
    try:
        fields = {
            "project": args.project,
            "issuetype": args.type,
            "summary": args.summary,
        }
        if args.description:
            fields["description"] = args.description
        if args.assignee:
            fields["assignee"] = args.assignee
        if args.priority:
            fields["priority"] = args.priority
        if args.labels:
            fields["labels"] = args.labels
        if args.parent:
            fields["parent"] = args.parent
        fields.update(parse_json_arg(args.fields))
        client = client_from_args(args)
        created = client.create_issue(fields, content_format=args.content_format)
        print(json.dumps({
            "status": "ok",
            "mcp": "createJiraIssue",
            "key": created.get("key"),
            "id": created.get("id"),
            "self": created.get("self"),
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError, json.JSONDecodeError) as exc:
        return emit_error(exc)


def cmd_jira_edit(args: argparse.Namespace) -> int:
    try:
        fields = parse_json_arg(args.fields)
        if args.summary:
            fields["summary"] = args.summary
        if args.description is not None:
            fields["description"] = args.description
        if args.assignee is not None:
            fields["assignee"] = args.assignee or None
        client = client_from_args(args)
        client.edit_issue(args.issue, fields, content_format=args.content_format)
        print(json.dumps({
            "status": "ok",
            "mcp": "editJiraIssue",
            "key": args.issue,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError, json.JSONDecodeError) as exc:
        return emit_error(exc)


def cmd_jira_transitions(args: argparse.Namespace) -> int:
    try:
        items = client_from_args(args).transitions(args.issue)
        print(json.dumps({
            "status": "ok",
            "key": args.issue,
            "transitions": [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "to": (item.get("to") or {}).get("name"),
                }
                for item in items
            ],
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def cmd_jira_transition(args: argparse.Namespace) -> int:
    try:
        client_from_args(args).transition(args.issue, args.to, parse_json_arg(args.fields) or None)
        print(json.dumps({
            "status": "ok",
            "mcp": "transitionJiraIssue",
            "key": args.issue,
            "to": args.to,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError, json.JSONDecodeError) as exc:
        return emit_error(exc)


def cmd_jira_attach(args: argparse.Namespace) -> int:
    try:
        client = client_from_args(args)
        if args.download:
            dest = args.output.expanduser() if args.output else Path(f"{args.download}.bin")
            path = client.download_attachment(args.download, dest)
            print(json.dumps({
                "status": "ok",
                "mcp": "downloadJiraIssueAttachment",
                "id": args.download,
                "output": str(Path(path).resolve()),
            }, indent=2, ensure_ascii=False, sort_keys=True))
            return 0
        if not args.issue or not args.file:
            raise ValueError("upload needs ISSUE FILE; download needs --download ID")
        uploaded = client.upload_attachment(args.issue, args.file.expanduser())
        print(json.dumps({
            "status": "ok",
            "mcp": "uploadAttachmentToJiraIssue",
            "key": args.issue,
            "attachments": uploaded if isinstance(uploaded, list) else [uploaded],
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def cmd_jira_link(args: argparse.Namespace) -> int:
    try:
        client_from_args(args).link_issues(args.issue, args.type, args.to)
        print(json.dumps({
            "status": "ok",
            "mcp": "jira-work-item-links-jira-work-item",
            "from": args.issue,
            "type": args.type,
            "to": args.to,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def cmd_jira_media_ids(args: argparse.Namespace) -> int:
    """Resolve the media UUIDs needed to embed existing attachments inline."""
    try:
        client = client_from_args(args)
        issue = client.request(
            "GET",
            f"/rest/api/3/issue/{urllib.parse.quote(args.issue)}",
            query={"fields": "attachment"},
        )
        attachments = (issue.get("fields") or {}).get("attachment") or []
        wanted = set(args.filename or [])
        rows = []
        for item in attachments:
            name = item.get("filename", "")
            if wanted and name not in wanted:
                continue
            rows.append({
                "filename": name,
                "attachmentId": str(item.get("id")),
                "mediaId": client.attachment_media_id(item.get("id")),
                "mimeType": item.get("mimeType"),
            })
        print(json.dumps({
            "status": "ok",
            "issue": args.issue,
            "attachments": rows,
            "unresolved": [r["filename"] for r in rows if not r["mediaId"]],
            "hint": (
                "Embed with --content-format adf|html using mediaId as the media node id. "
                "identify the PNG; data-width-type=pixel; figure data-width = PNG width; "
                "inner data-width/data-height = PNG width/height; layout wide if width>=1200 "
                "else center. Never percentage (PROJ-435 letterbox): "
                '<figure data-type="media-single" data-layout="wide" '
                'data-width="PNG_WIDTH" data-width-type="pixel">'
                '<div data-type="media" data-media-type="file" '
                'data-id="MEDIA_ID" data-collection="" data-alt="file.png" '
                'data-width="PNG_WIDTH" data-height="PNG_HEIGHT">'
                "</div></figure>"
            ),
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError, json.JSONDecodeError) as exc:
        return emit_error(exc)


def cmd_jira_request(args: argparse.Namespace) -> int:
    try:
        body = None
        if args.body_file:
            body = json.loads(args.body_file.expanduser().read_text(encoding="utf-8"))
        elif args.body:
            body = json.loads(args.body)
        result = client_from_args(args).request(args.method, args.path, body=body)
        print(json.dumps({
            "status": "ok",
            "mcp": "executeRead/executeWrite",
            "method": args.method.upper(),
            "path": args.path,
            "result": result,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError, json.JSONDecodeError) as exc:
        return emit_error(exc)


def cmd_jira_wiki_get(args: argparse.Namespace) -> int:
    try:
        result = client_from_args(args).wiki_get(args.content_id)
        print(json.dumps({
            "status": "ok",
            "mcp": "getConfluenceContent",
            "content": result,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def cmd_jira_wiki_search(args: argparse.Namespace) -> int:
    try:
        result = client_from_args(args).wiki_search(args.cql, args.limit)
        results = result.get("results") if isinstance(result, dict) else result
        print(json.dumps({
            "status": "ok",
            "mcp": "searchConfluence",
            "cql": args.cql,
            "count": len(results) if isinstance(results, list) else None,
            "results": results,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def cmd_jira_wiki_create(args: argparse.Namespace) -> int:
    try:
        body = args.body
        if args.body_file:
            body = args.body_file.expanduser().read_text(encoding="utf-8")
        if not body:
            raise ValueError("pass --body or --body-file")
        created = client_from_args(args).wiki_create(
            space=args.space,
            title=args.title,
            body=body,
            content_type=args.content_type,
            parent_id=args.parent,
        )
        print(json.dumps({
            "status": "ok",
            "mcp": "createConfluenceContent",
            "id": created.get("id") if isinstance(created, dict) else None,
            "title": created.get("title") if isinstance(created, dict) else None,
            "type": created.get("type") if isinstance(created, dict) else None,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def cmd_jira_wiki_update(args: argparse.Namespace) -> int:
    try:
        body = args.body
        if args.body_file:
            body = args.body_file.expanduser().read_text(encoding="utf-8")
        updated = client_from_args(args).wiki_update(
            args.content_id,
            title=args.title,
            body=body,
        )
        print(json.dumps({
            "status": "ok",
            "mcp": "updateConfluenceContent",
            "id": updated.get("id") if isinstance(updated, dict) else args.content_id,
            "version": (updated.get("version") or {}).get("number") if isinstance(updated, dict) else None,
        }, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, JiraError) as exc:
        return emit_error(exc)


def add_jira_parsers(group) -> None:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--token-file",
        type=Path,
        default=TOKEN_PATH,
        help="API token YAML (default ~/.agents/.auth/jira-api-token.yaml).",
    )
    parent.add_argument("--site", help="Override site URL (default from YAML or the token file).")
    parent.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds.")

    capabilities = group.add_parser(
        "capabilities",
        parents=[parent],
        help="List MCP-equivalent commands and token status.",
        description="Show which Atlassian MCP tools this CLI covers, and whether the API token file is present.",
    )
    capabilities.set_defaults(func=cmd_jira_capabilities)

    myself = group.add_parser(
        "myself",
        parents=[parent],
        help="Return the authenticated Jira user.",
        description="GET /rest/api/3/myself. MCP: atlassianUserInfo.",
    )
    myself.set_defaults(func=cmd_jira_myself)

    resources = group.add_parser(
        "resources",
        parents=[parent],
        help="Return site URL and current user.",
        description="serverInfo + myself. MCP: getAccessibleAtlassianResources.",
    )
    resources.set_defaults(func=cmd_jira_resources)

    get_parser = group.add_parser(
        "get",
        parents=[parent],
        help="Fetch one issue as JSON.",
        description="GET /rest/api/3/issue/{key} with comments filled. Drops Solutions Jira x GitLab comments by default. MCP: getJiraIssue.",
    )
    get_parser.add_argument("issue", help="Issue key or id.")
    get_parser.add_argument("--fields", help="Comma-separated Jira fields.")
    get_parser.add_argument("--format", choices=("markdown", "adf"), default="markdown")
    get_parser.add_argument("--output", type=Path, help="Write full JSON here; stdout stays bounded.")
    get_parser.add_argument(
        "--include-bots",
        action="store_true",
        help="Keep Solutions Jira x GitLab (and other filtered) comments.",
    )
    get_parser.add_argument(
        "--strict-bots",
        action="store_true",
        help="Also drop authors matching bot|gitlab|github|jenkins|bamboo|automation.",
    )
    get_parser.set_defaults(func=cmd_jira_get)

    fetch = group.add_parser(
        "fetch",
        parents=[parent],
        help="Download issue, comments, attachments, and write the PRD.",
        description=(
            "One-shot replacement for getJiraIssue + N downloadJiraIssueAttachment calls. "
            "Writes ~/.agents/prds/<KEY>.md via render_issue.py."
        ),
    )
    fetch.add_argument("issue", help="Issue key or id.")
    fetch.add_argument("--fields", help="Comma-separated Jira fields.")
    fetch.add_argument("--prd-root", type=Path, default=PRD_ROOT)
    fetch.add_argument("--no-attachments", action="store_true")
    fetch.add_argument("--save-raw", action="store_true", help="Also write <KEY>.json next to the PRD.")
    fetch.add_argument("--include-bots", action="store_true")
    fetch.add_argument("--strict-bots", action="store_true")
    fetch.set_defaults(func=cmd_jira_fetch)

    search = group.add_parser(
        "search",
        parents=[parent],
        help="Search issues with JQL.",
        description="POST /rest/api/3/search/jql. MCP: searchJiraIssuesUsingJql.",
    )
    search.add_argument("jql", help="JQL query.")
    search.add_argument("--fields", help="Comma-separated Jira fields.")
    search.add_argument("--max-results", type=int, default=50)
    search.add_argument("--next-page-token")
    search.add_argument("--full", action="store_true", help="Include full issue objects.")
    search.add_argument("--format", choices=("markdown", "adf"), default="markdown")
    search.add_argument("--include-bots", action="store_true")
    search.add_argument("--strict-bots", action="store_true")
    search.set_defaults(func=cmd_jira_search)

    comment = group.add_parser(
        "comment",
        parents=[parent],
        help="Add or edit an issue comment.",
        description="MCP: addOrEditJiraIssueComment. Markdown and HTML are converted to ADF; --content-format adf posts a raw ADF document unchanged.",
    )
    comment.add_argument("issue", help="Issue key or id.")
    comment.add_argument("--body", help="Comment markdown, or HTML/raw ADF JSON with --content-format html|adf. Use adf for media, mentions or tables: markdown cannot represent them.")
    comment.add_argument("--body-file", type=Path)
    comment.add_argument("--comment-id", help="Edit this comment id instead of adding.")
    comment.add_argument("--content-format", choices=("markdown", "html", "adf"), default="markdown")
    comment.add_argument("--visibility", help="group:NAME or role:NAME.")
    comment.add_argument("--internal", action="store_true", help="JSM internal note.")
    comment.set_defaults(func=cmd_jira_comment)

    media = group.add_parser(
        "media-ids",
        parents=[parent],
        help="Media UUIDs for an issue's attachments, for inline embedding.",
        description=(
            "Resolve the media file UUID of each attachment already on an issue. "
            "ADF media nodes are keyed by this UUID, not by the numeric attachment id, "
            "and no Jira REST field returns it -- it is read from the 303 Location of "
            "/rest/api/3/attachment/content/{id}. Use it to embed existing attachments "
            "inline without re-uploading them."
        ),
    )
    media.add_argument("issue", help="Issue key or id.")
    media.add_argument(
        "--filename",
        action="append",
        help="Limit to this filename. Repeatable. Default: every attachment.",
    )
    media.set_defaults(func=cmd_jira_media_ids)

    create = group.add_parser(
        "create",
        parents=[parent],
        help="Create an issue.",
        description="POST /rest/api/3/issue. MCP: createJiraIssue.",
    )
    create.add_argument("--project", required=True, help="Project key.")
    create.add_argument("--type", required=True, dest="type", help="Issue type name.")
    create.add_argument("--summary", required=True)
    create.add_argument("--description")
    create.add_argument("--assignee", help="Account id, email, or display-name query.")
    create.add_argument("--priority")
    create.add_argument("--labels")
    create.add_argument("--parent", help="Parent issue key.")
    create.add_argument("--fields", help="JSON object of additional fields (names or customfield_*).")
    create.add_argument("--content-format", choices=("markdown", "html", "adf"), default="markdown")
    create.set_defaults(func=cmd_jira_create)

    edit = group.add_parser(
        "edit",
        parents=[parent],
        help="Edit an issue.",
        description="PUT /rest/api/3/issue/{key}. MCP: editJiraIssue.",
    )
    edit.add_argument("issue")
    edit.add_argument("--fields", default="{}", help="JSON object of fields to set. null clears.")
    edit.add_argument("--summary")
    edit.add_argument("--description")
    edit.add_argument("--assignee")
    edit.add_argument("--content-format", choices=("markdown", "html", "adf"), default="markdown")
    edit.set_defaults(func=cmd_jira_edit)

    transitions = group.add_parser(
        "transitions",
        parents=[parent],
        help="List available transitions.",
        description="GET /rest/api/3/issue/{key}/transitions.",
    )
    transitions.add_argument("issue")
    transitions.set_defaults(func=cmd_jira_transitions)

    transition = group.add_parser(
        "transition",
        parents=[parent],
        help="Transition an issue by status name or id.",
        description="MCP: transitionJiraIssue.",
    )
    transition.add_argument("issue")
    transition.add_argument("--to", required=True, help="Transition name, destination status, or id.")
    transition.add_argument("--fields", help="JSON fields required by the transition.")
    transition.set_defaults(func=cmd_jira_transition)

    attach = group.add_parser(
        "attach",
        parents=[parent],
        help="Upload a file, or download one attachment by id.",
        description="MCP: uploadAttachmentToJiraIssue / downloadJiraIssueAttachment.",
    )
    attach.add_argument("issue", nargs="?", help="Issue key (required for upload).")
    attach.add_argument("file", nargs="?", type=Path, help="Local file to upload.")
    attach.add_argument("--download", metavar="ATTACHMENT_ID", help="Download this attachment id.")
    attach.add_argument("--output", type=Path, help="Destination path for --download.")
    attach.set_defaults(func=cmd_jira_attach)

    link = group.add_parser(
        "link",
        parents=[parent],
        help="Create a Jira issue link.",
        description="FROM --type Blocks --to TO means FROM blocks TO. MCP Teamwork Graph subset.",
    )
    link.add_argument("issue", help="Outward issue key.")
    link.add_argument("--type", required=True, dest="type", help="Link type name (Blocks, Relates, Duplicate).")
    link.add_argument("--to", required=True, help="Inward issue key.")
    link.set_defaults(func=cmd_jira_link)

    request = group.add_parser(
        "request",
        parents=[parent],
        help="Call an arbitrary Jira/Confluence REST path.",
        description="Escape hatch for MCP executeRead/executeWrite operations that have a REST equivalent.",
    )
    request.add_argument("method", help="HTTP method.")
    request.add_argument("path", help="Absolute URL or site-relative path starting with /.")
    request.add_argument("--body", help="JSON request body.")
    request.add_argument("--body-file", type=Path)
    request.set_defaults(func=cmd_jira_request)

    wiki_get = group.add_parser(
        "wiki-get",
        parents=[parent],
        help="Get Confluence content by id.",
        description="MCP: getConfluenceContent.",
    )
    wiki_get.add_argument("content_id")
    wiki_get.set_defaults(func=cmd_jira_wiki_get)

    wiki_search = group.add_parser(
        "wiki-search",
        parents=[parent],
        help="Search Confluence with CQL.",
        description="MCP: searchConfluence.",
    )
    wiki_search.add_argument("cql")
    wiki_search.add_argument("--limit", type=int, default=25)
    wiki_search.set_defaults(func=cmd_jira_wiki_search)

    wiki_create = group.add_parser(
        "wiki-create",
        parents=[parent],
        help="Create a Confluence page.",
        description="MCP: createConfluenceContent for type=page.",
    )
    wiki_create.add_argument("--space", required=True)
    wiki_create.add_argument("--title", required=True)
    wiki_create.add_argument("--body", help="Storage HTML (or wiki markup with care).")
    wiki_create.add_argument("--body-file", type=Path)
    wiki_create.add_argument("--content-type", default="page")
    wiki_create.add_argument("--parent", help="Parent content id.")
    wiki_create.set_defaults(func=cmd_jira_wiki_create)

    wiki_update = group.add_parser(
        "wiki-update",
        parents=[parent],
        help="Update a Confluence page.",
        description="MCP: updateConfluenceContent for type=page.",
    )
    wiki_update.add_argument("content_id")
    wiki_update.add_argument("--title")
    wiki_update.add_argument("--body")
    wiki_update.add_argument("--body-file", type=Path)
    wiki_update.set_defaults(func=cmd_jira_wiki_update)
