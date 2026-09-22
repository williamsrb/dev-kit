Cursor and Claude are separate products with separate session files. A delete, wipe, hide, archive, or "leave no trace" request applies **only** to the product the user named.

- **Cursor:** `composerHeaders`, `cursorDiskKV`, `composerData`, conversation-search, `~/.cursor/projects/**/agent-transcripts`, `~/.cursor/memory`, `glass.claudeCodeSessionRegistry.v1` visibility/archive flags that only change Cursor's sidebar.
- **Claude:** `~/.claude/projects/**/*.jsonl`, `~/.claude/session-env`, `~/.config/Claude/claude-code-sessions`, `~/.local/share/cursor-to-claude-sync/exports.json`.

These are **not** permission to write or delete the other product's store: same title (`[cursor] …`, `(1)`, import sibling), AgentMigration / `localComposerId` / registry association, export ledger dest UUID, "the other listing of this chat", or "leave no trace" after an order that named only one product.

Alter another product's files only when the user names that product (Cursor, Claude, Claude Desktop, `~/.claude`, Codex, or that session id) in the same order. If the user named one product and you think the other copy should go too, **stop and ask**.
