# How to keep Cursor and Claude session stores isolated

## Scope

Detail behind the always-loaded rule "Session store isolation" in `AGENTS.md`: which files belong to which product, and which look-alike signals are not permission to touch the other one.

## Procedure

- **Cursor:** `composerHeaders`, `cursorDiskKV`, `composerData`, conversation-search, `~/.cursor/projects/**/agent-transcripts`, `~/.cursor/memory`, `glass.claudeCodeSessionRegistry.v1` visibility/archive flags that only change Cursor's sidebar.
- **Claude:** `~/.claude/projects/**/*.jsonl`, `~/.claude/session-env`, `~/.config/Claude/claude-code-sessions`, `~/.local/share/cursor-to-claude-sync/exports.json`.

These are **not** permission to write or delete the other product's store: same title (`[cursor] …`, `(1)`, import sibling), AgentMigration / `localComposerId` / registry association, export ledger dest UUID, "the other listing of this chat", "leave no trace" after an order that named only one product, or "delete, not hide" when the hide was a Cursor archive flag.

Alter another product's files only when the user names that product (Cursor, Claude, Claude Desktop, `~/.claude`, Codex, or that session id) in the same order. If the user named one product and you think the other copy should go too, **stop and ask**.
Do not archive the other product's copy as a substitute for asking.

## Example

```text
# BAD: user says "Delete both [cursor] … chats on Cursor"
rm ~/.claude/projects/**/851e2e36-….jsonl
# also bad: delete Desktop indexes, or the export ledger row

# GOOD: Cursor rows, transcripts and search only. Leave Claude JSONL and indexes alone.
```
